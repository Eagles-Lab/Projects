packer {
  required_plugins {
    alicloud = {
      source  = "github.com/hashicorp/alicloud"
      version = "= 1.2.0"
    }
  }
}

variable "region" {
  type    = string
  default = "cn-hangzhou"
}

variable "source_image_id" {
  type        = string
  description = "同地域可用的 Rocky Linux 9 x86_64 镜像 ID"
}

variable "build_instance_type" {
  type        = string
  description = "构建时临时 ECS 的实例规格，需在目标地域有库存"
}

variable "image_name" {
  type        = string
  description = "新镜像名称；每次构建使用不同名称"
}

variable "ssh_username" {
  type        = string
  default     = "root"
  description = "源镜像的 SSH 登录用户，按源镜像实际情况修改"
}

source "alicloud-ecs" "rocky9" {
  region                      = var.region
  source_image                = var.source_image_id
  instance_type               = var.build_instance_type
  image_name                  = var.image_name
  image_description           = "IaC course Rocky Linux 9 base image; Kubernetes installed later by Ansible"
  ssh_username                = var.ssh_username
  ssh_timeout                 = "10m"
  associate_public_ip_address = true
  internet_charge_type        = "PayByTraffic"

  system_disk_mapping {
    disk_size = 40
  }

  run_tags = {
    Project = "iac-kubernetes-course"
    Role    = "image-build"
  }

  tags = {
    Project = "iac-kubernetes-course"
    Role    = "base-image"
  }
}

build {
  sources = ["source.alicloud-ecs.rocky9"]

  provisioner "shell" {
    script          = "${path.root}/scripts/base.sh"
    execute_command = "bash '{{ .Path }}'"
  }

}
