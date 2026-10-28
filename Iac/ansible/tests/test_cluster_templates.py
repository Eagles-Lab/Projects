"""离线检查镜像替换、VXLAN 配置、CA 校验和 kubelet 私网 IP。"""

import copy
import importlib.util
from pathlib import Path
import unittest

from ansible.errors import AnsibleFilterError
from ansible.plugins.filter.core import regex_search
from jinja2 import Environment, StrictUndefined
import yaml


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "roles/calico/filter_plugins/calico_manifest.py"
SPEC = importlib.util.spec_from_file_location("calico_manifest", PLUGIN)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPOSITORY = "dockerproxy.net/calico"


def sample_manifest():
    node = {
        "name": "calico-node",
        "image": "quay.io/calico/node:v3.33.0",
        "env": [{"name": "CLUSTER_TYPE", "value": "k8s,bgp"}],
        "livenessProbe": {"exec": {"command": ["calico", "--felix-live", "--bird-live"]}},
        "readinessProbe": {"exec": {"command": ["calico", "--felix-ready", "--bird-ready"]}},
    }
    return [
        {"kind": "ConfigMap", "metadata": {"name": "calico-config"}, "data": {"calico_backend": "bird"}},
        {"kind": "CustomResourceDefinition", "metadata": {"name": "ippools.crd.projectcalico.org"}},
        {"kind": "DaemonSet", "metadata": {"name": "calico-node"}, "spec": {"template": {"spec": {
            "containers": [node],
            "initContainers": [
                {"image": "quay.io/calico/calico:v3.33.0"},
                {"image": "quay.io/calico/third-party-cni-plugins:v3.33.0"},
            ],
        }}}},
        {"kind": "Deployment", "metadata": {"name": "calico-kube-controllers"}, "spec": {"template": {
            "spec": {"containers": [{"image": "quay.io/calico/calico:v3.33.0"}]},
        }}},
    ]


class CalicoTests(unittest.TestCase):
    def render(self, documents):
        raw = yaml.safe_dump_all(documents)
        return list(yaml.safe_load_all(MODULE.render_calico_manifest(raw, REPOSITORY, "v3.33.0", "192.168.0.0/16")))

    def test_vxlan_domestic_images_and_preserved_resources(self):
        source = sample_manifest()
        output = self.render(source)
        self.assertEqual(len(source), len(output))
        self.assertEqual(source[1], output[1])
        self.assertEqual(output[0]["data"]["calico_backend"], "vxlan")
        spec = output[2]["spec"]["template"]["spec"]
        node = spec["containers"][0]
        env = {item["name"]: item["value"] for item in node["env"]}
        self.assertEqual(env["CALICO_IPV4POOL_VXLAN"], "Always")
        self.assertEqual(env["CALICO_IPV4POOL_IPIP"], "Never")
        self.assertEqual(env["CALICO_IPV4POOL_CIDR"], "192.168.0.0/16")
        self.assertEqual(env["IP_AUTODETECTION_METHOD"], "kubernetes-internal-ip")
        self.assertEqual(env["CLUSTER_TYPE"], "k8s")
        for container in spec["containers"] + spec["initContainers"]:
            self.assertTrue(container["image"].startswith(REPOSITORY + "/"))
        self.assertNotIn("--bird-live", node["livenessProbe"]["exec"]["command"])
        self.assertNotIn("--bird-ready", node["readinessProbe"]["exec"]["command"])
        self.assertEqual(self.render(copy.deepcopy(source)), output)

    def test_unexpected_image_rejected(self):
        documents = sample_manifest()
        documents[2]["spec"]["template"]["spec"]["containers"][0]["image"] = "unknown.example/node:v3.33.0"
        with self.assertRaises(AnsibleFilterError):
            self.render(documents)

    def test_missing_resources_rejected(self):
        with self.assertRaises(AnsibleFilterError):
            self.render(sample_manifest()[:2])


class WorkerTests(unittest.TestCase):
    def test_join_uses_private_ip_token_and_ca_hash(self):
        environment = Environment(undefined=StrictUndefined)
        environment.filters["regex_search"] = regex_search
        raw = (ROOT / "roles/worker/templates/kubeadm-join.yaml.j2").read_text()
        ca_hash = "sha256:" + "a" * 64
        result = environment.from_string(raw).render(
            worker_control_plane="cp1", hostvars={"cp1": {"private_ip": "172.20.1.10"}},
            node_hostname="iac-test-worker", private_ip="172.20.1.11",
            worker_join_command={"stdout": "kubeadm join 172.20.1.10:6443 --token abcdef.0123456789abcdef --discovery-token-ca-cert-hash " + ca_hash},
        )
        config = yaml.safe_load(result)
        discovery = config["discovery"]["bootstrapToken"]
        self.assertEqual(discovery["apiServerEndpoint"], "172.20.1.10:6443")
        self.assertEqual(discovery["token"], "abcdef.0123456789abcdef")
        self.assertEqual(discovery["caCertHashes"], [ca_hash])
        self.assertNotIn("unsafeSkipCAVerification", discovery)
        self.assertEqual(config["nodeRegistration"]["kubeletExtraArgs"], [{"name": "node-ip", "value": "172.20.1.11"}])


if __name__ == "__main__":
    unittest.main()
