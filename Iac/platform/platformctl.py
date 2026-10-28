#!/usr/bin/env python3
"""本地教学平台入口：生成配置、部署、初始化作业、查看状态。Python 3.9+。"""
import argparse
import base64
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import shutil
import string
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def read_env():
    path = HERE / ".env"
    if not path.exists():
        raise ValueError("请先运行 python3 platformctl.py init --ssh-key /你的私钥.pem")
    result = {}
    for line in path.read_text().splitlines():
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            result[key] = value.strip("'")
    return result


def random_alnum(length):
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))


def initialize(key):
    if not (HERE / ".env").exists():
        if "'" in str(ROOT) or "\n" in str(ROOT):
            raise ValueError("项目路径不能含单引号或换行")
        values = {
            "IAC_PROJECT_DIR": str(ROOT), "DB_PASSWORD": secrets.token_hex(24),
            "REDIS_PASSWORD": secrets.token_hex(24), "NETBOX_SECRET_KEY": secrets.token_hex(40),
            "NETBOX_TOKEN_PEPPER": secrets.token_hex(40),
            "NETBOX_ADMIN_PASSWORD": "admin",
            "SEMAPHORE_ADMIN_PASSWORD": "admin",
            "SEMAPHORE_ACCESS_KEY_ENCRYPTION": base64.b64encode(secrets.token_bytes(32)).decode(),
        }
        for kind in ("READ", "WRITE"):
            values["NETBOX_%s_TOKEN_KEY" % kind] = random_alnum(12)
            values["NETBOX_%s_TOKEN_SECRET" % kind] = random_alnum(40)
        # 此处生成运行时配置；静态源文件中不保存实际密码。
        with os.fdopen(os.open(HERE / ".env", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as out:
            out.write("# 自动生成的本地机密，禁止提交或分享。保留本文件和数据卷配套使用。\n")
            out.writelines("%s='%s'\n" % pair for pair in values.items())
        print("网页登录使用 admin/admin；其他机密已随机生成：platform/.env（600 权限）")
    else:
        print("保留现有 .env，不重置密码、Token 或加密密钥")
    if read_env()["IAC_PROJECT_DIR"] != str(ROOT):
        raise ValueError("项目已移动，请在 .env 中更新 IAC_PROJECT_DIR 后继续")
    directory = HERE / "secrets"
    directory.mkdir(exist_ok=True, mode=0o700)
    if key:
        source = Path(key).expanduser().resolve()
        destination = directory / "ecs_ssh_key"
        if not source.is_file():
            raise ValueError("私钥文件不存在")
        if source != destination.resolve():
            shutil.copyfile(source, destination)
        destination.chmod(0o600)
        print("已复制 SSH 私钥到忽略目录，不改变原私钥")


def compose(*args, **kwargs):
    return subprocess.run(["docker", "compose", "--project-directory", str(HERE),
                           "--env-file", str(HERE / ".env"), "-f", str(HERE / "compose.yaml"),
                           *args], check=True, **kwargs)


def reset_admin():
    """只重置两个本地教学页面的密码，不动数据库密码、Token 或加密密钥。"""
    read_env()
    compose("exec", "-T", "semaphore", "semaphore", "user", "change-by-login",
            "--login", "admin", "--password", "admin", "--config", "/etc/semaphore/config.json")
    compose("exec", "-T", "netbox", "/opt/netbox/venv/bin/python", "/opt/netbox/netbox/manage.py",
            "shell", "--no-startup", "--no-imports", text=True, input=(
                "from django.contrib.auth import get_user_model, authenticate\n"
                "user = get_user_model().objects.get(username='admin')\n"
                "user.set_password('admin')\n"
                "user.save(update_fields=['password'])\n"
                "assert authenticate(username='admin', password='admin') is not None\n"
                "print('NetBox admin/admin 登录认证通过')\n"))
    # 更新 init 生成的本地运行时配置，保留其余随机机密及原有权限。
    path = HERE / ".env"
    names = {"NETBOX_ADMIN_PASSWORD", "SEMAPHORE_ADMIN_PASSWORD"}
    lines = path.read_text().splitlines()
    with path.open("w") as out:
        for line in lines:
            name = line.split("=", 1)[0]
            out.write((name + "='admin'" if name in names else line) + "\n")
    path.chmod(0o600)
    Semaphore(read_env())
    print("Semaphore admin/admin 登录认证通过；本地配置已同步，其他机密未修改。")


class Semaphore:
    def __init__(self, env):
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.base_url = "http://127.0.0.1:%s/api/" % env.get("SEMAPHORE_PORT", "3001")
        self.request("auth/login", {"auth": "admin", "password": env["SEMAPHORE_ADMIN_PASSWORD"]})

    def request(self, path, data=None, method=None):
        request = urllib.request.Request(self.base_url + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Content-Type": "application/json"}, method=method)
        try:
            with self.opener.open(request, timeout=30) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raise RuntimeError("Semaphore HTTP %s：%s（请查看平台日志）" % (exc.code, path)) from None

    def ensure(self, path, data):
        entries = self.request(path + "?sort=name&order=asc")
        matches = [entry for entry in entries if entry["name"] == data["name"]]
        if len(matches) > 1:
            raise ValueError("同名对象不唯一：" + data["name"])
        return matches[0] if matches else self.request(path, data)


def bootstrap():
    env = read_env()
    compose("exec", "-T", "netbox", "/opt/netbox/venv/bin/python", "/opt/netbox/netbox/manage.py",
            "shell", "--no-startup", "--no-imports", input=(HERE / "netbox/bootstrap.py").read_text(), text=True)
    api = Semaphore(env)
    project = api.ensure("projects", {"name": "IaC Lab", "alert": False, "max_parallel_tasks": 1})
    prefix = "project/%s/" % project["id"]
    key = api.ensure(prefix + "keys", {"name": "IaC local files", "type": "none", "project_id": project["id"]})
    repo = api.ensure(prefix + "repositories", {"name": "IaC workspace", "git_url": "/workspace",
        "git_branch": "main", "ssh_key_id": key["id"], "project_id": project["id"]})
    environment = api.ensure(prefix + "environment", {"name": "IaC runtime", "json": "{}", "env": "{}",
        "project_id": project["id"]})
    inventory = api.ensure(prefix + "inventory", {"name": "NetBox dynamic inventory", "type": "file",
        "inventory": "/workspace/ansible/inventory/netbox.yml", "ssh_key_id": key["id"], "project_id": project["id"]})
    jobs = [("00 检查执行环境", "check"), ("01 预览云资源计划", "plan"),
            ("02 创建云资源并登记 NetBox（收费）", "apply"), ("03 重新登记 NetBox", "import"),
            ("04 查看 NetBox 主机清单", "inventory"), ("05 Ansible 自动创建 Kubernetes", "cluster"),
            ("06 销毁云资源并更新 NetBox（删除）", "destroy"),
            ("07 Ansible 安装 Argo CD", "argocd")]
    for name, action in jobs:
        data = {"name": name, "project_id": project["id"], "type": "",
            "app": "ansible" if action == "argocd" else "bash",
            "repository_id": repo["id"], "environment_id": environment["id"],
            "inventory_id": inventory["id"],
            "playbook": "ansible/argocd.yml" if action == "argocd" else "platform/jobs/run.sh",
            "arguments": "[]" if action == "argocd" else json.dumps([action]),
            "allow_override_args_in_task": False, "allow_parallel_tasks": False}
        template = api.ensure(prefix + "templates", data)
        # 原地迁移旧的 07 Bash 模板，保留模板 ID 和任务历史；其他模板不改动。
        if action == "argocd" and any(template.get(k) != data[k] for k in ("app", "playbook", "arguments")):
            api.request(prefix + "templates/%s" % template["id"], {**template, **data}, method="PUT")
    print("Semaphore：IaC Lab 项目与 %s 个作业已就绪；没有启动任何云资源作业。" % len(jobs))


def verify():
    # 只读与离线验证：不调用云创建/销毁，也不 SSH 到真实节点。
    compose("exec", "-T", "semaphore", "bash", "/workspace/platform/jobs/run.sh", "check")
    compose("exec", "-T", "semaphore", "terraform", "-chdir=/workspace/terraform",
            "init", "-input=false", "-lockfile=readonly")
    compose("exec", "-T", "semaphore", "terraform", "-chdir=/workspace/terraform", "validate")
    compose("exec", "-T", "semaphore", "bash", "/workspace/platform/jobs/run.sh", "inventory")
    compose("exec", "-T", "semaphore", "ansible-playbook", "-i", "/workspace/ansible/inventory/netbox.yml",
            "/workspace/ansible/cluster.yml", "--syntax-check")
    compose("exec", "-T", "semaphore", "ansible-playbook", "-i", "/workspace/ansible/inventory/netbox.yml",
            "/workspace/ansible/argocd.yml", "--syntax-check")


def selftest():
    compose("exec", "-T", "semaphore", "python3", "/workspace/platform/tests/integration.py")
    api = Semaphore(read_env())
    project = next(p for p in api.request("projects") if p["name"] == "IaC Lab")
    prefix = "project/%s/" % project["id"]
    templates = api.request(prefix + "templates?sort=name&order=asc")
    for name in ("00 检查执行环境", "04 查看 NetBox 主机清单"):
        template = next(t for t in templates if t["name"] == name)
        task = api.request(prefix + "tasks", {"template_id": template["id"]})
        for _ in range(60):
            result = api.request(prefix + "tasks/%s" % task["id"])
            if result["status"] == "success":
                print("Semaphore 页面作业执行通过：" + name)
                break
            if result["status"] in ("error", "stopped"):
                raise RuntimeError("Semaphore 作业失败，请在页面查看日志：" + name)
            time.sleep(2)
        else:
            raise RuntimeError("Semaphore 验证作业未及时结束，请检查页面任务状态")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "up", "bootstrap", "verify", "selftest", "status", "logs", "stop", "credentials", "reset-admin"))
    parser.add_argument("--ssh-key", help="阿里云密钥对对应的本地 .pem 路径，只复制不上传")
    args = parser.parse_args()
    if args.command == "init":
        initialize(args.ssh_key)
    elif args.command == "reset-admin":
        reset_admin()
    elif args.command == "up":
        read_env()
        if shutil.disk_usage(ROOT).free < 10 * 1024 ** 3:
            raise ValueError("请先腾出至少 10 GiB 空间，不会自动清理你的 Docker 数据")
        compose("config", "--quiet")
        compose("up", "-d", "--build", "--wait", "--wait-timeout", "900")
        bootstrap()
        verify()
        print("完成：Semaphore http://localhost:%s；NetBox http://localhost:8000。账号都是 admin。" % read_env().get("SEMAPHORE_PORT", "3001"))
    elif args.command == "bootstrap":
        bootstrap()
    elif args.command == "verify":
        verify()
    elif args.command == "selftest":
        selftest()
    elif args.command == "status":
        compose("ps")
    elif args.command == "logs":
        compose("logs", "--tail", "80", "netbox", "semaphore")
    elif args.command == "stop":
        compose("stop")
        print("已停止本地平台，保留数据卷；不会清理云资源。")
    elif args.command == "credentials":
        env = read_env()
        print("当前本地平台登录密码：")
        print("NetBox admin：" + env["NETBOX_ADMIN_PASSWORD"])
        print("Semaphore admin：" + env["SEMAPHORE_ADMIN_PASSWORD"])


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, RuntimeError, urllib.error.URLError, subprocess.CalledProcessError) as exc:
        sys.exit(str(exc))
