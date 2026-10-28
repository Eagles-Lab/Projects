"""在实际连接节点之前，拒绝缺组、缺关键变量的动态 Inventory。"""
import ipaddress
import json
import sys


def plain_data(value):
    # 新版 ansible-inventory JSON 会显式包装“不可信字符串”。这里只做校验，
    # 解包供 IP/字段比较使用，不回写 Inventory，也不改变 Ansible 的信任标记。
    if isinstance(value, dict):
        if set(value) == {"__ansible_unsafe"}:
            return plain_data(value["__ansible_unsafe"])
        return {key: plain_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [plain_data(item) for item in value]
    return value


def validate(data):
    data = plain_data(data)
    cp = data.get("control_plane", {}).get("hosts", [])
    workers = data.get("workers", {}).get("hosts", [])
    if len(cp) != 1 or not workers:
        raise ValueError("需要恰好 1 个 control_plane 和至少 1 个 workers，请先交付并登记主机")
    for name in cp + workers:
        host = data["_meta"]["hostvars"][name]
        for field in ("ansible_host", "private_ip"):
            ipaddress.IPv4Address(host[field])
        if not host.get("node_hostname") or not host.get("node_role"):
            raise ValueError("主机缺少 node_hostname / node_role：" + name)
    print("Inventory 前置检查通过")


if __name__ == "__main__":
    try:
        validate(json.load(sys.stdin))
    except (ValueError, KeyError) as exc:
        sys.exit("Inventory 检查失败：" + str(exc))
