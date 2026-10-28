import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


inventory = load("check_inventory")
syncer = load("sync_netbox")


class ValidationTests(unittest.TestCase):
    def test_empty_inventory_rejected(self):
        with self.assertRaises(ValueError):
            inventory.validate({})

    def test_ansible_tagged_json(self):
        self.assertEqual(inventory.plain_data({"ip": {"__ansible_unsafe": "203.0.113.10"}}), {"ip": "203.0.113.10"})

    def test_complete_inventory(self):
        host = {"ansible_host": "203.0.113.10", "private_ip": "172.20.1.10",
                "node_hostname": "test", "node_role": "worker"}
        inventory.validate({"control_plane": {"hosts": ["cp"]}, "workers": {"hosts": ["wk"]},
                            "_meta": {"hostvars": {"cp": host, "wk": host}}})

    def test_multiple_control_planes_rejected(self):
        with self.assertRaises(ValueError):
            inventory.validate({"control_plane": {"hosts": ["cp1", "cp2"]}, "workers": {"hosts": ["wk"]}})

    def test_empty_nodes_rejected(self):
        with self.assertRaises(ValueError):
            syncer.validate_nodes({})

    def test_bad_node_address_rejected(self):
        with self.assertRaises(ValueError):
            syncer.validate_nodes({"cp": {"role": "control-plane", "public_ip": "REPLACE"}})

    def test_complete_node(self):
        nodes = {"cp": {"role": "control-plane", "public_ip": "203.0.113.10",
                         "private_ip": "172.20.1.10", "instance_id": "i-test", "host_name": "cp"}}
        self.assertEqual(syncer.validate_nodes(nodes), nodes)


if __name__ == "__main__":
    unittest.main()
