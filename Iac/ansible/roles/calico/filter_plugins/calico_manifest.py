"""保留官方 RBAC、CRD 和工作负载，仅调整镜像与 VXLAN 配置。"""

from ipaddress import ip_network

import yaml
from ansible.errors import AnsibleFilterError


def render_calico_manifest(content, repository, version, pod_subnet):
    documents = list(yaml.safe_load_all(content))
    network = ip_network(pod_subnet)
    if network.version != 4:
        raise AnsibleFilterError("当前教学方案仅支持 IPv4 Pod 网段")

    found = set()
    image_names = set()
    for document in documents:
        if not document:
            continue
        kind = document.get("kind")
        name = document.get("metadata", {}).get("name")
        if kind == "ConfigMap" and name == "calico-config":
            document["data"]["calico_backend"] = "vxlan"
            found.add("config")
        if kind not in ("DaemonSet", "Deployment"):
            continue

        spec = document["spec"]["template"]["spec"]
        for container in spec.get("initContainers", []) + spec.get("containers", []):
            image = container["image"]
            prefix = "quay.io/calico/"
            if not image.startswith(prefix) or not image.endswith(":" + version):
                raise AnsibleFilterError("官方清单镜像或版本变化，请先检查：" + image)
            image_name = image[len(prefix):].split(":")[0]
            image_names.add(image_name)
            container["image"] = repository.rstrip("/") + "/" + image[len(prefix):]

        if kind == "DaemonSet" and name == "calico-node":
            container = next(c for c in spec["containers"] if c["name"] == "calico-node")
            overrides = {
                "CLUSTER_TYPE": "k8s",
                "CALICO_IPV4POOL_CIDR": str(network),
                "CALICO_IPV4POOL_IPIP": "Never",
                "CALICO_IPV4POOL_VXLAN": "Always",
                "IP_AUTODETECTION_METHOD": "kubernetes-internal-ip",
            }
            container["env"] = [
                entry for entry in container.get("env", []) if entry["name"] not in overrides
            ] + [{"name": key, "value": value} for key, value in overrides.items()]
            # VXLAN 不使用 BGP，因此同步移除 BIRD 存活和就绪检查。
            for probe_name in ("livenessProbe", "readinessProbe"):
                command = container[probe_name]["exec"]["command"]
                container[probe_name]["exec"]["command"] = [
                    arg for arg in command if arg not in ("--bird-live", "--bird-ready")
                ]
            found.add("node")
        elif kind == "Deployment" and name == "calico-kube-controllers":
            found.add("controllers")

    if found != {"config", "node", "controllers"}:
        raise AnsibleFilterError("官方清单缺少预期的 Calico 资源，请检查下载内容")
    if image_names != {"calico", "node", "third-party-cni-plugins"}:
        raise AnsibleFilterError("官方清单镜像清单变化，请先核对国内镜像来源")
    return yaml.safe_dump_all(documents, allow_unicode=True, sort_keys=False, explicit_start=True)


class FilterModule:
    def filters(self):
        return {"iac_calico_manifest": render_calico_manifest}
