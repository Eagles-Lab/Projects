"""由 platformctl 通过 manage.py shell 执行，只初始化本课程对象。"""
import os

from django.contrib.auth import get_user_model
from core.models import ObjectType
from dcim.models import DeviceRole
from extras.models import CustomField, Tag
from users.models import Token
from virtualization.models import Cluster, ClusterType, VirtualMachine

User = get_user_model()
user, created = User.objects.get_or_create(username="admin", defaults={
    "is_superuser": True, "email": "admin@localhost",
})
if created:
    user.set_password(os.environ["ADMIN_PASSWORD"])
    user.save()

for kind, writable in (("WRITE", True), ("READ", False)):
    key = os.environ[kind + "_TOKEN_KEY"]
    if not Token.objects.filter(key=key).exists():
        Token.objects.create(user=user, version=2, key=key,
                             token=os.environ[kind + "_TOKEN_SECRET"],
                             write_enabled=writable, description="IaC " + kind)

for slug, name, color in (("control-plane", "Control plane", "2196f3"),
                          ("worker", "Worker", "4caf50")):
    DeviceRole.objects.get_or_create(slug=slug, defaults={
        "name": name, "color": color, "vm_role": True,
    })
cluster_type, _ = ClusterType.objects.get_or_create(
    slug="alicloud", defaults={"name": "Alibaba Cloud"})
Cluster.objects.get_or_create(name="iac-lab", defaults={"type": cluster_type})
Tag.objects.get_or_create(slug="iac-course", defaults={"name": "IaC Course", "color": "2196f3"})
for name, label in (("private_ip", "Private IP"),
                    ("cloud_instance_id", "Cloud instance ID"),
                    ("lifecycle", "Lifecycle (created / ready / deleted)")):
    field, _ = CustomField.objects.get_or_create(name=name, defaults={
        "label": label, "type": "text",
    })
    field.object_types.add(ObjectType.objects.get_for_model(VirtualMachine))
print("NetBox：管理员、V2 API Token、角色、集群与课程字段已就绪；未创建虚拟资产。")
