output "nodes" {
  description = "交给后续 Ansible/CMDB 使用的主机名、IP 和节点角色。"
  value = {
    for key, instance in alicloud_instance.nodes : key => {
      instance_id   = instance.id
      host_name     = instance.host_name
      role          = local.nodes[key].role
      private_ip    = instance.private_ip
      public_ip     = instance.public_ip
      instance_type = instance.instance_type
    }
  }
}

output "vpc_id" {
  description = "实验 VPC ID。"
  value       = alicloud_vpc.lab.id
}
