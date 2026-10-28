#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  exec sudo bash "$0" "$@"
fi

source /etc/os-release
if [[ "${ID}" != "rocky" || "${VERSION_ID}" != 9.* ]]; then
  echo "Expected Rocky Linux 9, got ${PRETTY_NAME}" >&2
  exit 1
fi

[[ "$(uname -m)" == x86_64 ]] || { echo 'Expected x86_64' >&2; exit 1; }


# 保留云镜像原有的软件源、网络、分区和 cloud-init 配置。
# 软件源替换须先验证镜像源可用，再单独添加，避免构建出无法更新的镜像。
dnf -y makecache
dnf -y install curl jq tar vim chrony
systemctl enable chronyd

# 安装与 Ansible 相同版本的 containerd（RPM 内含 runc），保留签名校验。
cat > /etc/yum.repos.d/iac-containerd.repo <<'EOF'
[iac-containerd]
name=containerd packages for EL9 (Alibaba Cloud mirror)
baseurl=https://mirrors.aliyun.com/docker-ce/linux/centos/9/$basearch/stable
gpgkey=https://mirrors.aliyun.com/docker-ce/linux/centos/gpg
gpgcheck=1
enabled=1
includepkgs=containerd.io
EOF
dnf -y install containerd.io-2.3.6-1.el9

mkdir -p /etc/containerd /etc/cni/net.d /opt/cni/bin
# 与 Ansible Role 保持一致：CRI、overlayfs、systemd cgroup 和国内 pause 镜像。
cat > /etc/containerd/config.toml <<'EOF'
version = 3
disabled_plugins = []

[grpc]
  address = "/run/containerd/containerd.sock"

[plugins."io.containerd.cri.v1.images"]
  snapshotter = "overlayfs"
  [plugins."io.containerd.cri.v1.images".pinned_images]
    sandbox = "registry.cn-hangzhou.aliyuncs.com/google_containers/pause:3.10.2"

[plugins."io.containerd.cri.v1.runtime".containerd]
  default_runtime_name = "runc"
  [plugins."io.containerd.cri.v1.runtime".containerd.runtimes.runc]
    runtime_type = "io.containerd.runc.v2"
    [plugins."io.containerd.cri.v1.runtime".containerd.runtimes.runc.options]
      SystemdCgroup = true

[plugins."io.containerd.cri.v1.runtime".cni]
  bin_dirs = ["/opt/cni/bin"]
  conf_dir = "/etc/cni/net.d"
EOF
containerd --config /etc/containerd/config.toml config dump >/dev/null
systemctl enable containerd
systemctl restart containerd
ctr plugins ls id==cri | grep -q 'ok'

# 固定版本、完整地址必须与 Ansible 保持一致；升级时同步更新这里。
images=(
  registry.cn-hangzhou.aliyuncs.com/google_containers/pause:3.10.2
  dockerproxy.net/calico/calico:v3.33.0
  dockerproxy.net/calico/node:v3.33.0
  dockerproxy.net/calico/third-party-cni-plugins:v3.33.0
  m.daocloud.io/quay.io/argoproj/argocd:v3.5.6
  m.daocloud.io/ghcr.io/dexidp/dex:v2.45.1
  m.daocloud.io/docker.io/library/redis:8.2.3-alpine
)
for image in "${images[@]}"; do
  echo "Pre-cache: ${image}"
  # 使用 Kubernetes 的 containerd namespace，并标记为 CRI 管理的镜像。
  ctr -n k8s.io images pull --platform linux/amd64 \
    --label io.cri-containerd.image=managed "$image"
done

# 停止服务后保存一致的磁盘数据；保留缓存与开机自启，不初始化集群。
systemctl stop containerd
sync
dnf clean all

echo "Base image prepared on ${PRETTY_NAME}"
