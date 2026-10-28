locals {
  name_prefix = "iac-${var.owner}"

  common_tags = {
    Project   = "iac-kubernetes-course"
    Owner     = var.owner
    Env       = "lab"
    ManagedBy = "terraform"
  }

  nodes = {
    control_plane = {
      host_name     = "${local.name_prefix}-cp"
      private_ip    = "172.20.1.10"
      instance_type = var.control_plane_instance_type
      role          = "control-plane"
    }
    worker = {
      host_name     = "${local.name_prefix}-worker"
      private_ip    = "172.20.1.11"
      instance_type = var.worker_instance_type
      role          = "worker"
    }
  }
}

resource "alicloud_vpc" "lab" {
  vpc_name   = "${local.name_prefix}-vpc"
  cidr_block = "172.20.0.0/16"
  tags       = local.common_tags
}

resource "alicloud_vswitch" "lab" {
  vpc_id       = alicloud_vpc.lab.id
  zone_id      = var.zone_id
  vswitch_name = "${local.name_prefix}-vswitch"
  cidr_block   = "172.20.1.0/24"
  tags         = local.common_tags
}

resource "alicloud_security_group" "cluster" {
  security_group_name = "${local.name_prefix}-sg"
  vpc_id              = alicloud_vpc.lab.id
  inner_access_policy = "Accept"
  tags                = local.common_tags
}

resource "alicloud_security_group_rule" "ssh" {
  type              = "ingress"
  ip_protocol       = "tcp"
  port_range        = "22/22"
  nic_type          = "intranet"
  policy            = "accept"
  priority          = 1
  security_group_id = alicloud_security_group.cluster.id
  cidr_ip           = var.ssh_cidr
}

resource "alicloud_instance" "nodes" {
  for_each = local.nodes

  instance_name = each.value.host_name
  host_name     = each.value.host_name
  image_id      = var.image_id
  instance_type = each.value.instance_type
  private_ip    = each.value.private_ip

  vswitch_id      = alicloud_vswitch.lab.id
  security_groups = [alicloud_security_group.cluster.id]
  key_name        = var.ssh_key_pair_name

  system_disk_category = "cloud_essd_entry"
  system_disk_size     = 40

  instance_charge_type       = "PostPaid"
  internet_charge_type       = "PayByTraffic"
  internet_max_bandwidth_out = var.public_bandwidth_mbps

  tags        = merge(local.common_tags, { Role = each.value.role })
  volume_tags = merge(local.common_tags, { Role = each.value.role })

  depends_on = [alicloud_security_group_rule.ssh]
}
