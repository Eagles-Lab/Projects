variable "access_key_id" {
  description = "阿里云 AccessKey ID，填写在本地 credentials.auto.tfvars 中，不提交 Git。"
  type        = string
  sensitive   = true
  ephemeral   = true

  validation {
    condition     = length(trimspace(var.access_key_id)) > 0 && var.access_key_id == trimspace(var.access_key_id)
    error_message = "请在 credentials.auto.tfvars 中填写 AccessKey ID，且不要包含首尾空白。"
  }
}

variable "access_key_secret" {
  description = "与 AccessKey ID 配对的 Secret，仅在本地保存，不写入 State 或计划文件。"
  type        = string
  sensitive   = true
  ephemeral   = true

  validation {
    condition     = length(trimspace(var.access_key_secret)) > 0 && var.access_key_secret == trimspace(var.access_key_secret)
    error_message = "请在 credentials.auto.tfvars 中填写配对的 AccessKey Secret，且不要包含首尾空白。"
  }
}

variable "region" {
  description = "阿里云地域，须与自定义镜像所在地域一致。"
  type        = string
  default     = "cn-hangzhou"
}

variable "zone_id" {
  description = "交换机和两台 ECS 所在可用区，例如 cn-hangzhou-j。"
  type        = string
}

variable "image_id" {
  description = "Packer 构建并保留的 Rocky Linux 9 自定义镜像 ID。"
  type        = string
}

variable "owner" {
  description = "个人资源标识，用于资源名称和标签；只用小写字母、数字和连字符。"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,18}[a-z0-9]$", var.owner)) && !strcontains(var.owner, "--")
    error_message = "owner 须为 2～20 位，以小写字母开头、字母或数字结尾，且不能连续使用连字符。"
  }
}

variable "ssh_cidr" {
  description = "允许 SSH 登录的本人公网 IP，必须是单个 IPv4 地址的 /32 网段。"
  type        = string
}

variable "ssh_key_pair_name" {
  description = "已在同地域阿里云 ECS 控制台创建的密钥对名称；不是 .pem 文件路径。"
  type        = string

  validation {
    condition     = length(trimspace(var.ssh_key_pair_name)) > 0
    error_message = "请填写已有的阿里云 ECS 密钥对名称。"
  }
}

variable "control_plane_instance_type" {
  description = "control-plane ECS 规格。"
  type        = string
  default     = "ecs.e-c1m2.large"
}

variable "worker_instance_type" {
  description = "worker ECS 规格。"
  type        = string
  default     = "ecs.e-c1m1.large"
}

variable "public_bandwidth_mbps" {
  description = "按流量计费公网 IP 的带宽上限，非固定带宽计费。"
  type        = number
  default     = 5

  validation {
    condition     = var.public_bandwidth_mbps >= 1 && var.public_bandwidth_mbps <= 100
    error_message = "public_bandwidth_mbps 须在 1～100 之间。"
  }
}
