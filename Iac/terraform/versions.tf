terraform {
  required_version = "~> 1.16.0"

  required_providers {
    alicloud = {
      source  = "aliyun/alicloud"
      version = "= 1.294.0"
    }
  }
}

provider "alicloud" {
  region     = var.region
  access_key = var.access_key_id
  secret_key = var.access_key_secret
}
