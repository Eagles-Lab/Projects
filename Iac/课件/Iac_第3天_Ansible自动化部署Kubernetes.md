# 第 3 天：Ansible 自动化部署 Kubernetes

使用现有 Ansible 工程交付一套两节点 Kubernetes 集群，并完成节点标签设置和 DNS 验证两项实践。

## 一、准备主机与 Inventory

### 1.1 重新创建云主机

在控制端执行：

```bash
cd /你的项目目录/Iac/terraform
terraform plan -var-file=local.tfvars
terraform apply -var-file=local.tfvars
terraform output nodes
```

记录两台主机的公网 IP、私网 IP 和 hostname。

### 1.2 更新 Inventory

进入 Ansible 目录，启用第一天准备的运行环境：

```bash
cd ../ansible
source .venv/bin/activate
```

编辑 `inventory/hosts.yml`，主机信息与 Terraform 输出保持一致。以下以 `owner = "allen"` 为例：

```yaml
all:
  children:
    control_plane:
      hosts:
        cp1:
          node_hostname: iac-allen-cp
          ansible_host: 控制节点公网IP
          private_ip: 172.20.1.10
          node_role: control-plane

    workers:
      hosts:
        worker1:
          node_hostname: iac-allen-worker
          ansible_host: 工作节点公网IP
          private_ip: 172.20.1.11
          node_role: worker

  vars:
    ansible_user: root
    ansible_ssh_private_key_file: /你的私钥路径/密钥.pem
    ansible_python_interpreter: /usr/bin/python3
```

| 字段 | 本项目中的用途 |
| --- | --- |
| `cp1`、`worker1` | Inventory 中的主机别名 |
| `ansible_host` | 控制端通过公网 SSH 连接的地址 |
| `private_ip` | Kubernetes 节点间通信使用的私网地址 |
| `node_hostname` | 系统主机名及 Kubernetes Node 名称 |
| `control_plane`、`workers` | 决定各 Playbook 阶段在哪些主机上运行 |

`ansible.cfg` 已指定默认 Inventory 为 `inventory/hosts.yml`。在当前目录测试：

```bash
ansible-inventory --graph
ansible all -m ping
```

两台主机均返回 `SUCCESS` 和 `"ping": "pong"` 后继续。

## 二、认识部署工程

```text
cluster.yml
  → bootstrap.yml：common → containerd → kubernetes
  → control_plane：初始化控制面
  → calico：安装网络插件
  → worker：加入工作节点
  → verify：检查节点与系统组件
```

| 文件或 Role | 主要作用 |
| --- | --- |
| `bootstrap.yml` | 在两台节点上执行系统、运行时和组件准备 |
| `roles/common` | hostname、时间同步、Swap、SELinux、内核参数等 |
| `roles/containerd` | 安装或检查 containerd，管理运行时配置 |
| `roles/kubernetes` | 安装 kubeadm、kubelet、kubectl 和配套工具 |
| `roles/control_plane` | 渲染 kubeadm 配置，初始化控制面 |
| `roles/calico` | 渲染并应用 Calico 清单，配置 Pod 网络 |
| `roles/worker` | 创建短期加入令牌，让 worker 加入集群 |
| `cluster.yml` | 串联上述流程并检查集群交付结果 |

## 三、初始化系统与容器运行时

### 3.1 执行基础初始化

```bash
ansible-playbook bootstrap.yml --syntax-check
ansible-playbook bootstrap.yml
```

两台节点都会执行以下操作：

| 阶段 | 主要配置 |
| --- | --- |
| 系统配置 | 设置 hostname 和私网解析，启用 chronyd，关闭 Swap |
| 教学环境访问策略 | 停用 firewalld，将已启用的 SELinux 设置为 permissive；节点访问仍受云安全组控制 |
| 内核与网络 | 加载 `overlay`、`br_netfilter`，启用 IP 转发等参数 |
| Calico 前置配置 | 避免 NetworkManager 管理 Calico 虚拟接口 |
| containerd | 配置 CRI、SystemdCgroup、pause 镜像及服务启动 |
| Kubernetes 组件 | 配置国内 RPM 源，安装固定版本组件 |

基础镜像已经预装 containerd，Ansible 仍负责检查软件版本、配置和服务状态，不需要每次卸载重装。

### 3.2 查看运行结果

在控制端执行：

```bash
ansible all -m command -a 'systemctl is-active containerd'
ansible all -m command -a 'swapon --show'
ansible all -m command -a 'sysctl net.ipv4.ip_forward'
ansible all -m command -a 'kubeadm version -o short'
```

预期 containerd 为 `active`，Swap 列表为空，`net.ipv4.ip_forward = 1`，kubeadm 版本与工程一致。

## 四、初始化 Kubernetes 控制面

### 4.1 认识 kubeadm 配置模板

`roles/control_plane/templates/kubeadm-init.yaml.j2` 会渲染到控制节点的 `/etc/kubernetes/kubeadm-init.yaml`。

主要参数对应关系：

| 模板字段 | 变量或值 | 作用 |
| --- | --- | --- |
| `localAPIEndpoint.advertiseAddress` | `private_ip` | 控制面 API 使用的节点私网 IP |
| `nodeRegistration.name` | `node_hostname` | 注册到集群中的节点名称 |
| `kubernetesVersion` | `control_plane_kubernetes_version` | 初始化的 Kubernetes 版本 |
| `clusterName` | `control_plane_cluster_name` | 本次集群名称 |
| `imageRepository` | `control_plane_image_repository` | 控制面配套镜像仓库 |
| `networking.podSubnet` | `control_plane_pod_subnet` | Pod 网段 |
| `networking.serviceSubnet` | `control_plane_service_subnet` | Service 网段 |
| `cgroupDriver` | `systemd` | 与 containerd 的 cgroup 配置保持一致 |

控制面镜像和 containerd 的 pause 镜像沿用工程中已配置的国内仓库。

### 4.2 执行控制面初始化

```bash
ansible-playbook cluster.yml --tags control_plane
```

该阶段渲染并校验配置、拉取镜像、执行 `kubeadm init`，再为控制节点 root 用户配置 kubectl。

登录控制节点，查看生成的配置和节点状态：

```bash
cat /etc/kubernetes/kubeadm-init.yaml
kubectl -n kube-system get configmap kubeadm-config -o yaml
kubectl get nodes -o wide
```

检查集群名称、Pod 网段和 Service 网段是否与 Role 的默认配置一致。网络插件尚未安装，此时控制节点可能为 `NotReady`。

## 五、安装 Calico 与加入 worker

### 5.1 安装 Calico

回到控制端的 `ansible` 目录：

```bash
ansible-playbook cluster.yml --tags calico
```

Role 会下载并缓存固定版本清单，渲染国内镜像地址和 VXLAN 配置，再应用到控制节点。Calico 的 Pod 地址池与 kubeadm 配置共同使用 `control_plane_pod_subnet`。

此阶段等待 Calico 节点插件就绪；Calico 控制器和 CoreDNS 的最终就绪状态在 worker 加入后统一检查。

### 5.2 加入工作节点

```bash
ansible-playbook cluster.yml --tags worker
```

加入流程已经由 `roles/worker` 实现：

1. 检查 worker 是否已有 `/etc/kubernetes/kubelet.conf`。
2. 在控制节点创建短期令牌，获取加入参数。
3. 将加入配置渲染到 worker，执行 `kubeadm join`。
4. 清理临时配置、撤销本次令牌，并设置 worker 角色标签。

不需要人工复制加入命令。已加入的节点会跳过首次加入流程。

### 5.3 检查两节点集群

```bash
ansible-playbook cluster.yml --tags verify
```

在控制节点查看：

```bash
kubectl get nodes -o wide
kubectl -n kube-system get pods -o wide
```

两台 Node 应为 `Ready`，Calico、CoreDNS 和控制面组件应正常运行。

## 六、实践一：用 Ansible 管理节点标签

### 6.1 增加一个标签任务

在 `roles/worker/tasks/main.yml` 末尾追加：

```yaml
- name: 给 worker 添加 workload 标签
  ansible.builtin.command:
    cmd: kubectl label node {{ node_hostname }} workload=demo --overwrite
  delegate_to: "{{ worker_control_plane }}"
```

任务在控制节点执行，为对应 worker 设置 `workload=demo`。`--overwrite` 允许更新已有同名标签。

### 6.2 执行并查看结果

```bash
ansible-playbook cluster.yml --tags worker
```

在控制节点查看：

```bash
kubectl get nodes -L workload
```

worker 的 `WORKLOAD` 列应显示 `demo`。下一节通过这个标签选择测试 Pod 的运行节点。

本例使用 `command`，重复执行仍会报告 `changed`，但同名标签不会重复添加。

## 七、实践二：使用 BusyBox 验证 DNS

### 7.1 给已有测试 Pod 增加节点选择条件

编辑工程已有的 `tests/busybox.yaml`，在 `spec` 下加入 `nodeSelector`，原有容器配置保持不变：

```yaml
spec:
  nodeSelector:
    workload: demo
```

该 Pod 使用工程中已有的国内 BusyBox 镜像，并调度到带有 `workload=demo` 标签的 worker。

### 7.2 编写一个测试 Playbook

在 `ansible` 目录新建 `test.yml`：

```yaml
---
- name: 部署测试 Pod 并检查 DNS
  hosts: control_plane
  become: true
  gather_facts: false
  tags: verify

  tasks:
    - name: 上传 BusyBox 清单
      ansible.builtin.copy:
        src: ../tests/busybox.yaml
        dest: /tmp/busybox.yaml
        mode: '0644'

    - name: 创建测试 Pod
      ansible.builtin.command: kubectl apply -f /tmp/busybox.yaml

    - name: 等待 Pod Ready
      ansible.builtin.command: kubectl -n default wait --for=condition=Ready pod/busybox --timeout=180s
      changed_when: false

    - name: 测试集群 DNS
      ansible.builtin.command: kubectl -n default exec busybox -- nslookup kubernetes.default.svc.cluster.local
      register: dns_result
      changed_when: false

    - name: 显示 DNS 解析结果
      ansible.builtin.debug:
        var: dns_result.stdout_lines
```

在控制端运行：

```bash
ansible-playbook test.yml
```

在控制节点查看 Pod 的运行位置：

```bash
kubectl -n default get pod busybox -o wide
```

Pod 应位于 worker，DNS 查询应返回 `kubernetes` Service 的 ClusterIP。Pod 就绪超时或 DNS 命令失败时，Playbook 会报错。

### 7.3 接入完整流程

在 `cluster.yml` 文件末尾追加，顶格书写：

```yaml
- import_playbook: test.yml
```

这样完整部署结束后，就会自动创建测试 Pod 并检查 DNS。

## 八、完整执行、重复验证与排错

### 8.1 使用统一入口

前面按阶段理解并验证流程后，执行完整入口：

```bash
ansible-playbook cluster.yml
```

该命令将系统准备、集群部署、节点标签和 DNS 验证串联起来。新建环境也可以在准备好 Inventory 和本日代码后，直接通过它完成部署。

重复执行时重点观察：

- 不重复执行 `kubeadm init`、`kubeadm join`。
- 配置未改变时，不应无故重启 containerd。
- 标签任务重复运行后，节点仍只有一个 `workload=demo` 标签。
- 测试 Pod 配置未改变时，`kubectl apply` 输出 `unchanged`；本例未定制其变更判定，Ansible 仍会报告 `changed`。
- DNS 检查每次执行，但不计为配置变更。


### 8.2 常见故障与检查入口

| 现象 | 优先检查 |
| --- | --- |
| Ansible `UNREACHABLE` | Inventory 公网 IP、SSH 私钥、云安全组 |
| 软件包安装失败 | 对应 RPM 源、版本及节点到源站的网络 |
| 镜像拉取慢或 `ImagePullBackOff` | Pod Events、具体镜像地址、缓存及仓库连通性 |
| worker 加入失败 | worker 到控制节点私网 6443 的连通性、kubelet 日志 |
| Node `NotReady` | containerd、kubelet、Calico 状态及 Pod 网段 |
| 测试 Pod `Pending` | 节点标签、`nodeSelector`、污点容忍及节点剩余资源 |
| DNS 测试失败 | CoreDNS 状态、测试 Pod 的 DNS 配置及 Pod 网络 |

控制节点上的常用检查命令：

```bash
kubectl -n kube-system get pods -o wide
kubectl -n default describe pod busybox
kubectl -n default exec busybox -- cat /etc/resolv.conf
```

在出现问题的节点查看：

```bash
systemctl status containerd kubelet --no-pager
journalctl -u kubelet -n 100 --no-pager
crictl images
```

## 九、本日实践任务与资源回收

### 9.1 必做任务

| 任务 | 完成标准 |
| --- | --- |
| 节点标签 | 通过 Ansible 给 worker 设置 `workload=demo`，并查询确认 |
| 集群验证 | 两个节点 Ready，BusyBox 调度到 worker，DNS 测试通过 |
| 完整执行 | 使用 `cluster.yml` 跑通全流程，能够说明重复执行时哪些任务跳过、哪些继续检查 |

### 9.2 拓展：增加一个 worker

在 Terraform 中增加一台 worker，更新 Inventory，再通过 Ansible 完成初始化和加入。验证新增节点 Ready、原节点保持正常后，回收额外资源。该任务会增加一台 ECS 及其系统盘的费用。

### 9.3 销毁当天云资源

实验结束后，在控制端保存代码，回到 Terraform 目录：

```bash
cd ../terraform
terraform destroy -var-file=local.tfvars
terraform state list
```

核对本工程管理的 ECS、系统盘和网络资源已释放。保留代码、State 和基础镜像；第四天重新创建环境，再将已验证的流程接入平台。
