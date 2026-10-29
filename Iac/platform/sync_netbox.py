"""Terraform outputs -> NetBox。仅维护带 iac-course 标签的本项目 VM。"""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


class NetBox:
    def __init__(self):
        self.url = os.environ.get("NETBOX_API", "http://netbox:8080").rstrip("/") + "/api/"
        self.token = os.environ["NETBOX_WRITE_TOKEN"]

    def request(self, path, data=None, method=None):
        request = urllib.request.Request(self.url + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Authorization": "Bearer " + self.token,
                     "Content-Type": "application/json"}, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            # 不输出请求头或 Token；服务端验证错误仅涉及资产字段。
            detail = exc.read().decode()[:1500]
            raise RuntimeError("NetBox HTTP %s (%s): %s" % (exc.code, path, detail)) from None

    def find(self, path, **filters):
        result = self.request(path + "?" + urllib.parse.urlencode(filters))
        if result["count"] > 1:
            raise ValueError("匹配到多个对象，拒绝猜测：" + path)
        return result["results"][0] if result["results"] else None

    def require(self, path, **filters):
        obj = self.find(path, **filters)
        if not obj:
            raise ValueError("请先初始化平台，未找到：" + path)
        return obj["id"]


def validate_nodes(nodes):
    if not isinstance(nodes, dict) or not nodes:
        raise ValueError("Terraform 未输出有效 nodes；请先创建资源")
    seen = set()
    for node in nodes.values():
        if node.get("role") not in ("control-plane", "worker"):
            raise ValueError("无法识别节点角色")
        for field in ("public_ip", "private_ip"):
            ipaddress.IPv4Address(node[field])
        if not node.get("instance_id") or not node.get("host_name"):
            raise ValueError("节点缺少 instance_id / host_name")
        if node["host_name"] in seen:
            raise ValueError("节点主机名重复")
        seen.add(node["host_name"])
    return nodes


def sync(nodes, state, api):
    validate_nodes(nodes)
    cluster = api.require("virtualization/clusters/", name="iac-lab")
    tag = api.require("extras/tags/", slug="iac-course")
    for node in nodes.values():
        name = node["host_name"]
        vm = api.find("virtualization/virtual-machines/", name=name, cluster_id=cluster)
        if vm and not any(t["slug"] == "iac-course" for t in vm["tags"]):
            raise ValueError("同名 VM 不是本课程资产，拒绝覆盖：" + name)
        same_instance = vm and vm["custom_fields"].get("cloud_instance_id") == node["instance_id"]
        if state in ("active", "offline") and not same_instance:
            raise ValueError("资产实例 ID 不匹配，拒绝回写：" + name)
        status = state
        if state == "staged" and same_instance and vm["status"]["value"] == "active":
            status = "active"
        fields = {
            "name": name, "cluster": cluster,
            "role": api.require("dcim/device-roles/", slug=node["role"]),
            "status": status,
            "tags": sorted(set([tag] + ([t["id"] for t in vm["tags"]] if vm else []))),
            "custom_fields": {"private_ip": node["private_ip"],
                              "cloud_instance_id": node["instance_id"]},
        }
        if vm:
            vm = api.request("virtualization/virtual-machines/%s/" % vm["id"], fields, "PATCH")
        else:
            vm = api.request("virtualization/virtual-machines/", fields)
        if state != "offline":
            interface = api.find("virtualization/interfaces/", virtual_machine_id=vm["id"], name="management")
            if not interface:
                interface = api.request("virtualization/interfaces/", {"virtual_machine": vm["id"], "name": "management"})
            address = node["public_ip"] + "/32"
            ip = api.find("ipam/ip-addresses/", address=address)
            if ip and ip.get("assigned_object_id") is not None and (
                ip.get("assigned_object_id") != interface["id"] or
                ip.get("assigned_object_type") != "virtualization.vminterface"
            ):
                raise ValueError("公网 IP 已分配给其他对象，拒绝覆盖：" + address)
            assignment = {"address": address, "status": "active",
                          "assigned_object_type": "virtualization.vminterface", "assigned_object_id": interface["id"]}
            if ip:
                ip = api.request("ipam/ip-addresses/%s/" % ip["id"], assignment, "PATCH")
            else:
                ip = api.request("ipam/ip-addresses/", assignment)
            api.request("virtualization/virtual-machines/%s/" % vm["id"], {"primary_ip4": ip["id"]}, "PATCH")
        print("%s -> %s" % (name, status))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes-file", type=Path)
    parser.add_argument("--status", choices=("staged", "active", "offline"), default="staged")
    args = parser.parse_args()
    if args.nodes_file:
        nodes = json.loads(args.nodes_file.read_text())
    else:
        nodes = json.loads(subprocess.check_output(
            ["terraform", "output", "-json", "nodes"], cwd=ROOT / "terraform", text=True))
    sync(nodes, args.status, NetBox())


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, RuntimeError, urllib.error.URLError) as exc:
        sys.exit(str(exc))
