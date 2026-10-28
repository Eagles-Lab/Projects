#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
action="${1:?Missing action}"
cd "$project_dir"

case "$action" in
  check)
    terraform version
    ansible --version
    ansible-galaxy collection list netbox.netbox
    python3 -c 'import pynetbox; print("pynetbox 可用")'
    ;;
  plan|apply|destroy)
    cd terraform
    test -s local.tfvars || { echo '请先配置 terraform/local.tfvars'; exit 1; }
    test -s credentials.auto.tfvars || { echo '请先配置 terraform/credentials.auto.tfvars'; exit 1; }
    terraform init -input=false -lockfile=readonly
    test "$(terraform workspace show)" = default || { echo '只允许 default workspace'; exit 1; }
    if [[ "$action" == plan ]]; then
      terraform plan -input=false -var-file=local.tfvars
    elif [[ "$action" == apply ]]; then
      terraform apply -input=false -auto-approve -var-file=local.tfvars
      python3 ../platform/sync_netbox.py
    else
      nodes_file="$(mktemp)"
      trap 'rm -f "$nodes_file"' EXIT
      terraform output -json | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin).get("nodes", {}).get("value", {})))' > "$nodes_file"
      terraform destroy -input=false -auto-approve -var-file=local.tfvars
      if python3 -c 'import json,sys; sys.exit(not bool(json.load(open(sys.argv[1]))))' "$nodes_file"; then
        python3 ../platform/sync_netbox.py --nodes-file "$nodes_file" --status deleted
      else
        echo 'State 中没有 nodes 输出，无需回写 NetBox'
      fi
    fi
    ;;
  import)
    python3 platform/sync_netbox.py
    ;;
  inventory)
    cd ansible
    ansible-inventory -i inventory/netbox.yml --graph
    ;;
  cluster)
    test -s "${IAC_SSH_PRIVATE_KEY_FILE:?SSH key path is missing}" || { echo '请先通过 init --ssh-key 配置私钥'; exit 1; }
    cd ansible
    # 空 Inventory 不允许静默跳过，必须有 1 个控制面及至少 1 个 worker。
    ansible-inventory -i inventory/netbox.yml --list | python3 ../platform/check_inventory.py
    ansible all -i inventory/netbox.yml -m ping
    ansible-playbook -i inventory/netbox.yml cluster.yml
    python3 ../platform/sync_netbox.py --status ready
    ;;
  *) echo "Unknown action: $action" >&2; exit 2 ;;
esac
