# 第 1 天：IaC 基础与 Packer 镜像制作


## 一、Iac概念

### 1.1 IaC 是什么

IaC 是 Infrastructure as Code，即基础设施即代码。

它的核心思想是：**将服务器、网络、存储和系统配置等基础设施要求写成代码，由工具按照代码完成创建、配置、变更与回收，而不是完全依赖人工操作。**

这里的“代码”不一定是 Python、Java 这样的应用程序，也可以是 Terraform 的 HCL 配置、Ansible 的 YAML 剧本，或 Packer 模板配合 Shell 脚本。不同工具负责不同层面的工作。

**从手工创建主机到代码化交付**

假设需要创建两台云主机，并安装相同版本的 containerd：

- 传统方式：登录控制台，分别选择实例规格、镜像、网络和磁盘；创建后逐台 SSH 登录，安装软件、修改配置，再手工记录操作。
- IaC 方式：将资源要求和安装步骤保存为配置文件，先检查内容，再由 Terraform 创建主机、Ansible 配置系统；需要重新交付时复用这套代码。

两者最终都需要调用云平台能力、操作系统和软件安装程序。区别在于，**IaC 把交付要求和操作流程固化为可管理的代码，减少重复点击、命令复制和对个人记忆的依赖。**

**用 Terraform 举例**

```hcl
# 概念示例，不是可以直接执行的完整配置。
resource "alicloud_instance" "worker" {
  instance_type = "目标实例规格"  # 希望使用什么规格的 ECS
  image_id      = "基础镜像 ID"   # 使用哪份操作系统镜像创建
}
```

这段配置表达的是“我需要一台符合这些要求的 ECS”，并不是逐条描述在控制台点击哪个按钮：

- `resource`：声明要管理一个资源。
- `alicloud_instance`：资源类型，表示阿里云 ECS 实例。
- `worker`：该资源在 Terraform 工程中的名称，不等同于云主机的实际 hostname，也不会自动赋予 Kubernetes worker 角色。
- 花括号内的参数：描述这台 ECS 应满足的要求。真实工程还需要网络、安全组等配置。

执行时，Terraform 通过 Provider 调用阿里云 API，结合配置、State 和云端查询结果生成执行计划；确认后再创建或调整资源。修改配置文件本身不会立即修改云主机，仍需要执行相应命令。具体过程将在第二天实践。

**为什么要把基础设施写成代码**

1. **可重复**：环境销毁后，可以用代码重新创建，而不是重新整理全部操作步骤。
2. **可检查**：规格、版本和配置集中保存在文件里，便于发现遗漏和差异。
3. **可追溯**：通过 Git 记录谁修改了什么，也可以在执行前进行评审。
4. **可复用**：调整参数后复用相同的交付逻辑，减少为每套环境重新编写流程。




## 二、准备本地工具与工程

### 2.1 本机条件

- 控制端：Rocky Linux 9 x86_64，建议 16 GiB 内存。
- 云端构建环境：阿里云 ECS。

### 2.2 获取课程工程

```bash
cd /你的项目目录/Iac
pwd
ls
```

```text
Iac/
├── packer/
│   ├── rocky9.pkr.hcl
│   ├── local.pkrvars.hcl
│   └── scripts/base.sh
├── terraform/
├── ansible/
├── platform/       # 第四天使用，今天不启动
├── gitops/
└── README.md
```

### 2.3 工具版本与安装

| 工具 | 课程要求 | 检查命令 |
| --- | --- | --- |
| Git | 用于后续管理项目代码和应用配置 | git --version |
| Packer | 当前样板使用 1.16.1 | packer version |
| Packer Alicloud 插件 | 模板固定为 1.2.0 | 由 packer init 安装 |
| Terraform | 工程要求 1.16.x | terraform version |
| Python | 本地 Ansible 已验证使用 3.13 | python3.13 --version |
| Ansible Core | 2.21.5 | ansible --version |
| kubectl | 建议与集群 1.36.5 对齐 | kubectl version --client |

**1. 安装基础工具**

```bash
sudo dnf install -y curl unzip
```

**2. 安装 Packer 1.16.1**

```bash
curl -fLO https://releases.hashicorp.com/packer/1.16.1/packer_1.16.1_linux_amd64.zip
unzip -o packer_1.16.1_linux_amd64.zip packer
sudo install -m 0755 packer /usr/local/bin/packer
packer version
```

**3. 安装 Terraform 1.16.6**

```bash
curl -fLO https://releases.hashicorp.com/terraform/1.16.6/terraform_1.16.6_linux_amd64.zip
unzip -o terraform_1.16.6_linux_amd64.zip terraform
sudo install -m 0755 terraform /usr/local/bin/terraform
terraform version
```

**4. 使用阿里云源安装 kubectl 1.36.5**

以 root 用户执行：

```bash
echo '[iac-kubectl]
name=Kubernetes kubectl v1.36 (Alibaba Cloud mirror)
baseurl=https://mirrors.aliyun.com/kubernetes-new/core/stable/v1.36/rpm/
enabled=1
gpgcheck=1
gpgkey=https://mirrors.aliyun.com/kubernetes-new/core/stable/v1.36/rpm/repodata/repomd.xml.key
includepkgs=kubectl' > /etc/yum.repos.d/iac-kubectl.repo
dnf install -y kubectl-1.36.5-150500.1.1
kubectl version --client
```

**5. 安装 Ansible Core 2.21.5**

```bash
python3.13 -m venv ansible/.venv
source ansible/.venv/bin/activate
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple ansible-core==2.21.5
ansible --version
```

安装参考：[Packer](https://developer.hashicorp.com/packer/install)、[Terraform](https://developer.hashicorp.com/terraform/install)、[kubectl](https://kubernetes.io/docs/tasks/tools/)。

## 三、准备个人云账号与成本提醒

### 3.1 个人账号与权限

每人准备独立的阿里云账号并完成实名认证，地域统一为杭州 `cn-hangzhou`，准备课程所需的资源操作权限。

### 3.2 凭据准备

- **AccessKey ID / Secret**：供 Packer、Terraform 调用云 API。
- **ECS 密钥对与私钥**：供后续 SSH、Ansible 登录主机。

凭据和私钥仅在本人本地保存，不提交 Git、不对外分享。

### 3.3 费用准备

- 预留约 100 元充值预算，实际消费以账单为准。
- Packer 构建、ECS、云盘、公网及保留的镜像快照可能产生费用。
- 设置费用提醒，实验结束后检查并释放不再需要的资源；提醒不会自动销毁资源。

## 四、Packer 的工作原理

### 4.1 Packer 是什么

Packer 是镜像构建工具，通过模板声明构建使用的云平台、源镜像、临时实例规格和执行脚本，最终生成可复用的基础镜像。

本项目的构建过程：

```text
本机执行 packer build
    → 插件调用阿里云 API 创建临时构建机
    → 使用源镜像启动 Rocky Linux 9
    → Packer 通过 SSH 将 base.sh 传入并执行
    → 脚本安装 containerd，下载后续需要的容器镜像
    → 将系统盘制作成 ECS 自定义镜像
    → 正常完成时清理插件管理的临时资源
```

### 4.2 Packer 与 Terraform 的关系

- Packer 回答：“创建主机时使用哪份已经准备好的系统镜像？”
- Terraform 回答：“创建几台主机，使用什么网络、规格与镜像？”
- Ansible 回答：“主机创建后，怎样配置并加入集群？”

后续 Terraform 使用的是 Packer 输出的镜像 ID，不是 base.sh 文件。

## 五、看懂三个核心文件

### 5.1 rocky9.pkr.hcl：构建模板

[阿里云packer文件示例](https://help.aliyun.com/zh/ecs/user-guide/use-packer-to-create-a-custom-image?spm=a2c4g.11186623.help-menu-25365.d_0_2_2_10_3_0.7a651202aIJefg&scm=20140722.H_60822._.OR_help-T_cn~zh-V_1)

模板声明构建规则，重点认识五类配置：

| 配置 | 作用 |
| --- | --- |
| packer / required_plugins | 声明所需插件及版本 |
| variable | 声明可传入的参数及默认值 |
| source "alicloud-ecs" "rocky9" | 定义阿里云构建机的配置 |
| build / sources | 选择本次构建使用的 source |
| provisioner "shell" | 指定构建机内要执行的脚本 |

插件配置：

```hcl
packer {
  required_plugins {
    alicloud = {
      source  = "github.com/hashicorp/alicloud"
      version = "= 1.2.0"
    }
  }
}
```

Packer 自身负责组织流程；Alicloud 插件运行在本机，负责调用阿里云 API 完成创建实例、制作镜像和清理等云操作。这里的 GitHub 标识是插件来源标识，不是把你的构建任务交给 GitHub 执行。

关键参数：

| 参数 | 当前含义 |
| --- | --- |
| region | 构建地域，默认 cn-hangzhou |
| source_image | 用于启动构建机的源镜像 ID |
| instance_type | 临时构建机规格，不是后续集群最终规格 |
| image_name | 新自定义镜像名称，每次构建避免重名 |
| ssh_username | 登录源镜像使用的 SSH 用户，按镜像实际情况填写 |
| ssh_timeout | 等待 SSH 可连接的超时，不是整个构建任务的总时限 |
| associate_public_ip_address | 请求公网访问相关能力，以当前插件实际创建结果为准 |
| internet_charge_type | 当前采用 PayByTraffic，公网按流量方式计费，具体项目以账单为准 |
| system_disk_mapping / disk_size | 构建系统盘容量，当前为 40 GiB |
| run_tags / tags | 分别标识构建实例与产物镜像，便于查找和追踪 |

当前模板没有固定 VPC、交换机和安全组 ID，构建时由插件处理临时网络。此处不是“不需要网络”；仍需确认实际 SSH 暴露范围、安全组规则和临时资源清理。

模板没有额外配置第二套 Ansible 流程，也不需要先启动 Docker 或运维平台。

### 5.2 local.pkrvars.hcl：构建参数

参数文件给模板中的变量赋具体值，不负责执行构建。

直接使用现有的 `packer/local.pkrvars.hcl`，构建时通过 `-var-file=local.pkrvars.hcl` 加载。

### 5.3 base.sh：构建机内执行的 Shell 脚本

Packer 将脚本上传到临时 ECS 执行，配置结果会保留在产出的基础镜像中。

当前脚本依次完成：

1. 检查 root 权限、Rocky Linux 9、x86_64 架构。
2. 检查是否存在旧集群的关键配置，避免将已初始化的集群作为源镜像打包。
3. 安装 curl、jq、tar、vim、chrony 等基础工具。
4. 配置国内 RPM 源，安装固定版本 containerd.io，软件包中包含 runc。
5. 配置 CRI、overlayfs、systemd cgroup 和国内 pause 镜像。
6. 启动 containerd，检查 CRI 插件。
7. 下载七个固定版本的容器镜像。
8. 停止 containerd、同步磁盘并清理软件包缓存；保留容器镜像数据。

需要区分：停止 containerd 是为了打包前收尾，不会取消其开机自启设置；新 ECS 上还会由 Ansible 检查配置、启动并验证服务。

### 5.4 预缓存哪些镜像

| 类别 | 镜像 | 当前版本 |
| --- | --- | --- |
| Pod 沙箱 | pause | 3.10.2 |
| Calico | calico、node、third-party-cni-plugins | v3.33.0 |
| Argo CD | argocd | v3.5.6 |
| Argo CD 依赖 | dex | v2.45.1 |
| Argo CD 依赖 | redis | 8.2.3-alpine |


## 六、实操：从验证到构建

### 6.1 本地语法检查与插件安装

在 packer 目录执行：

```bash
packer version
packer init rocky9.pkr.hcl
packer fmt -check rocky9.pkr.hcl
packer validate -syntax-only rocky9.pkr.hcl
```

这些命令不会创建 ECS。init 安装模板要求的插件，不等于开始构建。

fmt -check 仅检查格式；不通过时使用 packer fmt rocky9.pkr.hcl 格式化，再重新检查。语法正确不代表镜像 ID、库存、权限和下载链路已经可用。

### 6.2 在本机准备云 API 凭据

在 `packer/.env` 中保存凭据：

```bash
export ALICLOUD_ACCESS_KEY="你的AccessKey ID"
export ALICLOUD_SECRET_KEY="你的AccessKey Secret"
```

在 packer 目录加载后执行构建命令：

```bash
source .env
```

`.env` 已加入 Git 忽略，仅在本地保存。

### 6.3 完整配置验证

使用现有参数文件执行：

```bash
packer validate -var-file=local.pkrvars.hcl rocky9.pkr.hcl
```

这一步验证配置，不创建构建机，也不能替代真实构建及产物检查。


### 6.4 构建前确认

运行 build 前，确认：

- 使用本人目标账号，地域正确。
- 源镜像、构建规格及权限已核对。
- image_name 为本次构建的新名称。
- 了解构建、网络和镜像保留可能产生费用。
- 没有在其他终端重复运行同一次构建。
- 正在操作 packer 目录，而不是对已有集群手动执行 base.sh。

### 6.5 开始收费的云端构建

**镜像存储费用**：按关联标准快照容量 **7 GB**、杭州示例单价 **0.12 元/GB/月**估算：

| 保存时间 | 预计存储费用 |
| --- | ---: |
| 1 天 | 0.028 元 |
| 5 天 | 0.14 元 |
| 30 天 | 0.84 元 |

计算方式：`7 × 0.12 ÷ 30 × 保存天数`。实际按小时计费，单价以控制台报价为准；以上不含构建期间的 ECS、云盘和公网费用。[快照计费说明](https://help.aliyun.com/zh/ecs/snapshots-1)

- 查容量：ECS 控制台 → 杭州 → 快照 → 快照链 → 快照容量。
- 查单价：ECS 定价详情页 → 快照 → 杭州。
- 查扣费：费用与成本 → 账单明细 → 快照存储相关计费项。

确认后执行：

```bash
packer build -var-file=local.pkrvars.hcl rocky9.pkr.hcl
```

观察日志中的阶段：

| 日志阶段 | 含义 |
| --- | --- |
| 找到源镜像 | 插件正在核对构建输入 |
| 创建网络、实例、临时密钥等 | 已开始实际创建云资源，按实际资源计费 |
| 等待 SSH | 本机需要连到临时构建机 |
| 执行 Shell / Pre-cache | 在构建机上安装软件并下载镜像 |
| 创建自定义镜像 | 正在生成产物 |
| 清理临时资源 | 插件尝试释放它管理的临时资源 |

若镜像下载很慢，构建会持续占用临时 ECS，不能把等待时间当作免费时间。第一次构建需要完整下载，预缓存主要节省以后重复建机的时间。

### 6.6 如何判断成功

同时检查：

1. 命令退出成功，输出中出现产物信息。
2. 阿里云同地域的自定义镜像列表中出现本次名称及镜像 ID，状态可用。
3. 日志中的临时 ECS、网络和 EIP 等资源已按实际情况回收。

参考：[阿里云 Packer 镜像构建](https://help.aliyun.com/zh/ecs/user-guide/use-packer-to-create-a-custom-image)、[Packer 官方安装说明](https://developer.hashicorp.com/packer/install)。
