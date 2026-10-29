"""容器内运行：用临时文档地址验证集成，再删除本次测试资产，不访问云 API。"""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sync_netbox import NetBox, sync
from check_inventory import plain_data

ROOT = Path(__file__).resolve().parents[2]
api = NetBox()
prefix = "iac-selftest-" + uuid.uuid4().hex[:8]
nodes = {
    "control_plane": {"host_name": prefix + "-cp", "role": "control-plane",
                      "instance_id": "selftest-cp", "public_ip": "203.0.113.250", "private_ip": "172.20.1.250"},
    "worker": {"host_name": prefix + "-wk", "role": "worker",
               "instance_id": "selftest-wk", "public_ip": "203.0.113.251", "private_ip": "172.20.1.251"},
}


def inventory():
    return plain_data(json.loads(subprocess.check_output(["ansible-inventory", "-i", "inventory/netbox.yml", "--list"],
                                                       cwd=ROOT / "ansible", text=True)))


try:
    request = urllib.request.Request(api.url + "virtualization/virtual-machines/", data=b"{}",
        headers={"Authorization": "Bearer " + os.environ["NETBOX_TOKEN"], "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(request, timeout=20)
        raise AssertionError("只读 Token 不应允许写操作")
    except urllib.error.HTTPError as exc:
        assert exc.code == 403, "只读 Token 写权限校验异常"
    for node in nodes.values():
        if api.find("ipam/ip-addresses/", address=node["public_ip"] + "/32"):
            raise ValueError("测试地址已存在，拒绝占用")
    sync(nodes, "staged", api)
    data = inventory()
    cp, wk = [node["host_name"] for node in nodes.values()]
    assert cp in data.get("control_plane", {}).get("hosts", []), "控制面分组错误"
    assert wk in data.get("workers", {}).get("hosts", []), "worker 分组错误"
    for node in nodes.values():
        host = data["_meta"]["hostvars"][node["host_name"]]
        assert host["ansible_host"] == node["public_ip"], (host["ansible_host"], node["public_ip"])
        assert host["private_ip"] == node["private_ip"]
        assert host["node_hostname"] == node["host_name"]
        assert host["node_role"] == node["role"]
    sync(nodes, "active", api)
    sync(nodes, "staged", api)  # 相同实例重新登记不能将 active 降级。
    for node in nodes.values():
        vm = api.find("virtualization/virtual-machines/", name=node["host_name"])
        assert vm["status"]["value"] == "active"
    sync(nodes, "offline", api)
    for node in nodes.values():
        vm = api.find("virtualization/virtual-machines/", name=node["host_name"])
        assert vm["status"]["value"] == "offline"
    data = inventory()
    assert not any(node["host_name"] in data.get("_meta", {}).get("hostvars", {}) for node in nodes.values())
    print("集成测试通过：资产登记、分组/变量、状态回写、删除后清单排除；没有申请云资源。")
finally:
    for node in nodes.values():
        vm = api.find("virtualization/virtual-machines/", name=node["host_name"])
        if vm:
            ip = api.find("ipam/ip-addresses/", address=node["public_ip"] + "/32")
            interface = api.find("virtualization/interfaces/", virtual_machine_id=vm["id"], name="management")
            api.request("virtualization/virtual-machines/%s/" % vm["id"], {"primary_ip4": None}, "PATCH")
            if ip and interface and ip["assigned_object_type"] == "virtualization.vminterface" and ip["assigned_object_id"] == interface["id"]:
                api.request("ipam/ip-addresses/%s/" % ip["id"], method="DELETE")
            api.request("virtualization/virtual-machines/%s/" % vm["id"], method="DELETE")
    print("本次临时测试资产已清理，不删除任何真实云资源。")
