"""离线检查 Argo CD 镜像替换，不连接集群。"""
from pathlib import Path
import unittest

from jinja2 import Environment, FileSystemLoader
import yaml

ROLE = Path(__file__).resolve().parents[1] / "roles/argocd"


class ArgoCDTemplateTests(unittest.TestCase):
    def test_only_images_and_pull_policy_change(self):
        source = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: argocd-server
spec:
  template:
    spec:
      containers:
        - image: quay.io/argoproj/argocd:v3.5.6
          imagePullPolicy: Always
        - image: ghcr.io/dexidp/dex:v2.45.1
        - image: public.ecr.aws/docker/library/redis:8.2.3-alpine
      # 上游清单中的模板字符串不应被二次渲染。
      note: '{{ unchanged }}'
"""
        variables = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
        variables["argocd_image"] = variables["argocd_image"].replace(
            "{{ argocd_version }}", variables["argocd_version"])
        env = Environment(loader=FileSystemLoader(ROLE / "templates"))
        env.globals["lookup"] = lambda *args: source
        actual = yaml.safe_load(env.get_template("install.yaml.j2").render(**variables))
        expected = yaml.safe_load(source)
        containers = expected["spec"]["template"]["spec"]["containers"]
        for container, key in zip(containers, ("argocd_image", "argocd_dex_image", "argocd_redis_image")):
            container["image"] = variables[key]
            if container.get("imagePullPolicy") == "Always":
                container["imagePullPolicy"] = "IfNotPresent"
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
