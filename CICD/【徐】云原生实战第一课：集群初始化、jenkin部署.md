### 云原生实战第一次课程教案
项目：部门调整 需要重新部署一套CICD平台以供我们部门的开发测试运维使用

项目上线：产品提需求--->需求评审---》代码开发 --》 提交测试 --》 编译打包 --》 应用部署（本地开发：dev  test --》 pre --> prod)

---

#### 课程目标
1. 理解 Kubernetes 存储体系（PV/PVC/StorageClass）
2. 实现 Jenkins 数据持久化与高可用访问
3. k8s服务对外暴露学习
4. 部署Gitlab到k8s集群并且与Jenkins集成

---

#### 整体规划
开发人员在本地merge完毕代码，push到代码仓库之后，如果是develop开发分支的代码则发布到k8s测试环境，如果是master分支的代码则发布到k8s生产环境。

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1757205617484-2d34cd46-6c2f-4e40-8b42-ced4630995b6.png)

| 角色 | 作用 | 配置 |
| --- | --- | --- |
| k8s集群-测试环境 | 测试环境，用于rd执行各种测试 | 2核2G |
| k8s集群-生产环境 | 生产环境有两个重要的名称空<br/>间, 一个product代表真正的生产<br/>另外一个是staging代表预生产 | 2核2G |
| k8s集群-工具集群 | 存放各种管理工具：<br/>1、安装jenkins<br/>2、安装gitlab<br/>3、安装harbor | 8核16G |
| 开发机 | 安装git，编写代码后推送到<br/>gitlab里 | 1核512M |
| nfs服务器 | 存储 | 2核2G |


### **第一部分：K8S部署**
#### 1.1 基础环境配置
配置静态ip地址

略

关闭NetworkManager

```yaml
systemctl stop NetworkManager
systemctl disable NetworkManager
```

关闭selinux和防火墙

```yaml
sed -i 's/SELINUX=enforcing/SELINUX=disabled/' /etc/sysconfig/selinux
sed -i 's/SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config
setenforce 0
systemctl stop firewalld.service
systemctl disable firewalld.service
```

关闭swap分区

```yaml
#Kubernetes1.8开始要求关闭系统的Swap，如果不关闭，默认配置下kubelet将无法启动,所以我们有两种处理方式，采用一种即可
方式一：关闭swap分区
swapoff -a #先临时关闭，立即生效
sed -i 's/.*swap.*/#&/' /etc/fstab #注释掉swap，永久关闭，保证即便重启主机也会生效
方式二：kubelet忽略swap
echo 'KUBELET_EXTRA_ARGS="--fail-swap-on=false"' > /etc/sysconfig/kubelet
```



配置主机名

hostnamectl set-hostname xxx

配置yum源

```plain
mv /etc/yum.repos.d/CentOS-Base.repo /etc/yum.repos.d/CentOS-Base.repo.backup
cd /etc/yum.repos.d/
curl -o /etc/yum.repos.d/CentOS-Base.repo https://mirrors.aliyun.com/repo/Centos-7.repo
清除缓存：yum clean all
生成缓存：yum makecache
```

更新系统软件排除内核

yum install epel-release -y && yum update -y --exclud=kernel*

安装基础常用软件

```yaml
yum install wget expect vim net-tools ntp bash-completion ipvsadm ipset jq iptables conntrack sysstat libseccomp lrzsz -y
 
# 其他（选做）
yum -y install python-setuptools python-pip gcc gcc-c++ autoconf libjpeg libjpeg-devel libpng libpng-devel freetype freetype-devel libxml2 libxml2-devel \
zlib zlib-devel glibc glibc-devel glib2 glib2-devel bzip2 bzip2-devel zip unzip ncurses ncurses-devel curl curl-devel e2fsprogs \
e2fsprogs-devel krb5-devel libidn libidn-devel openssl openssh openssl-devel nss_ldap openldap openldap-devel openldap-clients \
openldap-servers libxslt-devel libevent-devel ntp libtool-ltdl bison libtool vim-enhanced python wget lsof iptraf strace lrzsz \
kernel-devel kernel-headers pam-devel tcl tk cmake ncurses-devel bison setuptool popt-devel net-snmp screen perl-devel \
pcre-devel net-snmp screen tcpdump rsync sysstat man iptables sudo libconfig git  bind-utils \
tmux elinks numactl iftop bwm-ng net-tools expect
```

更新系统内核（docker对系统内核要求比较高，最好使用4.4+），非必须操作，推荐做（注意：3.x内核与5.x内核加载的ipvs模块名是不同的，后续加载时需要注意一下）

之前可以通过yum直接升级

```yaml
# 1、升级系统内核
 
#查看 yum 中可升级的内核版本
yum list kernel --showduplicates
#如果list中有需要的版本可以直接执行 update 升级，多数是没有的，所以要按以下步骤操作
 
#导入ELRepo软件仓库的公共秘钥
rpm --import https://www.elrepo.org/RPM-GPG-KEY-elrepo.org
 
#Centos7系统安装ELRepo
yum -y install https://www.elrepo.org/elrepo-release-7.el7.elrepo.noarch.rpm
#Centos8系统安装ELRepo
#yum -y install https://www.elrepo.org/elrepo-release-8.el8.elrepo.noarch.rpm
 
#查看ELRepo提供的内核版本
yum --disablerepo="*" --enablerepo="elrepo-kernel" list available
 
#(1) kernel-lt：表示longterm，即长期支持的内核，会不断修复一些错误；当前为5.4.208。建议安装lt版
yum --enablerepo=elrepo-kernel install kernel-lt.x86_64 -y
 
#(2) kernel-ml：表示mainline，即当前主线的内核；会加入一些新功能。
# 若想安装主线内核则执行: yum --enablerepo=elrepo-kernel install kernel-ml.x86_64 -y
 
#查看系统可用内核，并设置启动项
sudo awk -F\' '$1=="menuentry " {print i++ " : " $2}' /etc/grub2.cfg
 
#0 : CentOS Linux (5.17.1-1.el7.elrepo.x86_64) 7 (Core)
#1 : CentOS Linux (3.10.0-1160.53.1.el7.x86_64) 7 (Core)
#2 : CentOS Linux (3.10.0-1160.el7.x86_64) 7 (Core)
#3 : CentOS Linux (0-rescue-20220208145000711038896885545492) 7 (Core)
 
#指定开机启动内核版本
grub2-set-default 0 # 或者 grub2-set-default 'CentOS Linux (5.17.1-1.el7.elrepo.x86_64) 7 (Core)'
 
#生成 grub 配置文件
grub2-mkconfig -o /boot/grub2/grub.cfg
 
#查看当前默认启动的内核
grubby --default-kernel
 
#重启系统，验证
uname -r
```

但是注意，ELRepo源仓库的el7的内核仓库去年已被清空,yum在线更新内核已不可用。

<font style="background-color:rgb(249, 242, 244);">解决思路：1、下载内核包编译，较复杂不推荐 2、重新找一个RPM包</font>

[https://github.com/omaidb/centos7_kernel_rpm](https://github.com/omaidb/centos7_kernel_rpm)

```plain
wget -c https://media.githubusercontent.com/media/omaidb/centos7_kernel_rpm/refs/heads/main/Centos7_kernel_lt_rpm/kernel-lt-5.4.278-1.el7.elrepo.x86_64.rpm
wget -c https://media.githubusercontent.com/media/omaidb/centos7_kernel_rpm/refs/heads/main/Centos7_kernel_lt_rpm/kernel-lt-devel-5.4.278-1.el7.elrepo.x86_64.rpm
wget -c https://media.githubusercontent.com/media/omaidb/centos7_kernel_rpm/refs/heads/main/Centos7_kernel_lt_rpm/kernel-lt-headers-5.4.278-1.el7.elrepo.x86_64.rpm

# 安装内核的rpm包
rpm -ivh *.rpm

# 如果报错则忽略依赖强制安装
rpm -ivh *.rpm --nodeps --force
```

设置升级之后的内核开机优先

1、grub文件 2、grubby命令



#### 1.2 配置docker、k8s
添加阿里云docker仓库

```plain
 yum install yum-utils -y
yum-config-manager --add-repo https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
```

安装docker(1.18版本的k8s，所以docker版本也需要指定和其适配的版本)

```plain
yum install  -y docker-ce-20.10.22-3.el7 docker-ce-cli-20.10.22-3.el7 docker-ce-rootless-extras-20.10.22-3.el7 docker-scan-plugin-0.23.0-3.el7
systemctl start docker
docker --version
```



配置镜像源

```plain
[root@node02 ~]#  cat /etc/docker/daemon.json 
{ 
  "exec-opts": ["native.cgroupdriver=systemd"],
  "live-restore":true,
  "registry-mirrors" : [
    "https://docker.registry.cyou",
    "https://docker-cf.registry.cyou",
    "https://dockercf.jsdelivr.fyi",
    "https://docker.jsdelivr.fyi",
    "https://dockertest.jsdelivr.fyi",
    "https://mirror.aliyuncs.com",
    "https://dockerproxy.com",
    "https://mirror.baidubce.com",
    "https://docker.m.daocloud.io",
    "https://docker.nju.edu.cn",
    "https://docker.mirrors.sjtug.sjtu.edu.cn",
    "https://docker.mirrors.ustc.edu.cn",
    "https://mirror.iscas.ac.cn",
    "https://docker.rainbond.cc",
    "https://do.nark.eu.org",
    "https://dc.j8.work",
    "https://dockerproxy.com",
    "https://gst6rzl9.mirror.aliyuncs.com",
    "https://registry.docker-cn.com",
    "http://hub-mirror.c.163.com",
    "http://mirrors.ustc.edu.cn/",
    "https://mirrors.tuna.tsinghua.edu.cn/",
    "http://mirrors.sohu.com/"
  ],
  "insecure-registries" : [
    "registry.docker-cn.com",
    "docker.mirrors.ustc.edu.cn"
  ],
  "debug": true,
  "experimental": false
}
systemctl restart docker
```

拉取镜像到本地

kubeadm部署时会去指定的地址拉取镜像，该地址在墙外无法访问，所以我们从阿里云拉取，并tag为指定的地址即可

```plain
#1、=====>编写脚本
cat > dockpullImages1.18.1.sh << EOF
#!/bin/bash
##所需要的镜像名字
#k8s.gcr.io/kube-apiserver:v1.18.1
#k8s.gcr.io/kube-controller-manager:v1.18.1
#k8s.gcr.io/kube-scheduler:v1.18.1
#k8s.gcr.io/kube-proxy:v1.18.1
#k8s.gcr.io/pause:3.2
#k8s.gcr.io/etcd:3.4.3-0
#k8s.gcr.io/coredns:1.6.7
###拉取镜像
docker pull registry.cn-hangzhou.aliyuncs.com/google_containers/kube-apiserver:v1.18.1
docker pull registry.cn-hangzhou.aliyuncs.com/google_containers/kube-controller-manager:v1.18.1
docker pull registry.cn-hangzhou.aliyuncs.com/google_containers/kube-scheduler:v1.18.1
docker pull registry.cn-hangzhou.aliyuncs.com/google_containers/kube-proxy:v1.18.1
docker pull registry.cn-hangzhou.aliyuncs.com/google_containers/pause:3.2
docker pull registry.cn-hangzhou.aliyuncs.com/google_containers/etcd:3.4.3-0
docker pull registry.cn-hangzhou.aliyuncs.com/google_containers/coredns:1.6.7
###修改tag
docker tag registry.cn-hangzhou.aliyuncs.com/google_containers/kube-apiserver:v1.18.1 k8s.gcr.io/kube-apiserver:v1.18.1
docker tag registry.cn-hangzhou.aliyuncs.com/google_containers/kube-controller-manager:v1.18.1 k8s.gcr.io/kube-controller-manager:v1.18.1
docker tag registry.cn-hangzhou.aliyuncs.com/google_containers/kube-scheduler:v1.18.1 k8s.gcr.io/kube-scheduler:v1.18.1
docker tag registry.cn-hangzhou.aliyuncs.com/google_containers/kube-proxy:v1.18.1 k8s.gcr.io/kube-proxy:v1.18.1
docker tag registry.cn-hangzhou.aliyuncs.com/google_containers/pause:3.2 k8s.gcr.io/pause:3.2
docker tag registry.cn-hangzhou.aliyuncs.com/google_containers/etcd:3.4.3-0 k8s.gcr.io/etcd:3.4.3-0
docker tag registry.cn-hangzhou.aliyuncs.com/google_containers/coredns:1.6.7 k8s.gcr.io/coredns:1.6.7
 
EOF
 
# 2、执行该脚本
sh dockpullImages1.18.1.sh
```

3、安装kubelet、kubeadm 和 kubectl

kubelet运行在Cluster所有节点上，负责启动Pod和容器。

kubeadm用于初始化Cluster。

kubectl是Kubernetes命令行工具。通过kubectl可以部署和管理应用，查看各种资源，创建、删除和更新各种组件。

```plain
cat <<EOF > /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://mirrors.aliyun.com/kubernetes/yum/repos/kubernetes-el7-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://mirrors.aliyun.com/kubernetes/yum/doc/yum-key.gpg https://mirrors.aliyun.com/kubernetes/yum/doc/rpm-package-key.gpg
EOF
 
sed -ri 's/gpgcheck=1/gpgcheck=0/g' /etc/yum.repos.d/kubernetes.repo 
```

安装

```plain
1.安装
yum makecache fast
# 注意，如果直接执行 yum install -y kubelet kubeadm kubectl ipvsadm 默认是下载最新版本v1.22.2
======================================================================
[root@master ~]# yum install -y kubelet-1.18.1-0.x86_64 kubeadm-1.18.1-0.x86_64 kubectl-1.18.1-0.x86_64 ipvsadm 
 
2.加载ipvs相关内核模块
yum install -y conntrack-tools ipvsadm ipvsadmin ipset conntrack libseccomp 
 
如果重新开机，需要重新加载（可以写在 /etc/rc.local 中开机自动加载）
modprobe ip_vs
modprobe ip_vs_rr
modprobe ip_vs_wrr
modprobe ip_vs_sh
#modprobe nf_conntrack_ipv4 # 如果是3.x内核，那么应该加载这一行
modprobe nf_conntrack # 如果是高版本内核比如5.x，那么应该加载这个。在高版本内核已经把nf_conntrack_ipv4替换为nf_conntrack了。
 
3.编辑文件添加开机启动
cat >> /etc/rc.local << EOF
modprobe ip_vs
modprobe ip_vs_rr
modprobe ip_vs_wrr
modprobe ip_vs_sh
modprobe nf_conntrack
#modprobe nf_conntrack_ipv4 # 如果是3.x内核，那么应该加载这一行、注释掉上面那一行
 
EOF
 
chmod +x /etc/rc.local
 
4.配置：
配置转发相关参数，否则可能会出错
cat <<EOF >  /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
vm.swappiness=0
EOF
 
5.使配置生效
sysctl --system
 
6.如果net.bridge.bridge-nf-call-iptables报错，加载br_netfilter模块
# modprobe br_netfilter
# sysctl -p /etc/sysctl.d/k8s.conf
 
7.查看是否加载成功
[root@master ~]# lsmod | grep ip_vs
ip_vs_sh               16384  0 
ip_vs_wrr              16384  0 
ip_vs_rr               16384  0 
ip_vs                 159744  6 ip_vs_rr,ip_vs_sh,ip_vs_wrr
nf_conntrack          151552  5 xt_conntrack,nf_nat,nf_conntrack_netlink,xt_MASQUERADE,ip_vs
nf_defrag_ipv6         24576  2 nf_conntrack,ip_vs
libcrc32c              16384  4 nf_conntrack,nf_nat,xfs,ip_vs
```

启动kubelet

```plain
#1.配置kubelet使用pause镜像
#配置变量：
systemctl start docker && systemctl enable docker
DOCKER_CGROUPS=$(docker info | grep 'Cgroup Driver' | cut -d' ' -f4)
echo $DOCKER_CGROUPS
 
#这个是使用国内的源。-###注意我们使用谷歌的镜像--操作下面的第3标题
#2.配置kubelet的cgroups
cat >/etc/sysconfig/kubelet<<EOF
KUBELET_EXTRA_ARGS="--cgroup-driver=$DOCKER_CGROUPS --pod-infra-container-image=registry.cn-hangzhou.aliyuncs.com/google_containers/pause-amd64:3.2"
EOF
 
# 上述操作本质就是写了类似下面的内容
#cat >/etc/sysconfig/kubelet<<EOF
#KUBELET_EXTRA_ARGS="--cgroup-driver=cgroupfs --pod-infra-container-image=k8s.gcr.io/pause:3.2"
#EOF

systemctl daemon-reload
systemctl enable kubelet && systemctl restart kubelet
 
# 注意在这里使用 # systemctl status kubelet，你会发现报错误信息；
# 7月 10 23:28:36 master systemd[1]: Unit kubelet.service entered failed state.
# 7月 10 23:28:36 master systemd[1]: kubelet.service failed.
 
#运行 # journalctl -xefu kubelet 命令查看systemd日志会发现提示缺少一些问题件
#这个错误在运行kubeadm init 生成CA证书后会被自动解决，此处可先忽略。
#简单地说就是在kubeadm init 之前kubelet会不断重启。
```

初始化master注意修改apiserver-advertise-address为master节点ip

```plain
kubeadm init \
--kubernetes-version=v1.18.1 \
--service-cidr=10.96.0.0/12 \
--pod-network-cidr=10.244.0.0/16 \
--apiserver-advertise-address=192.168.198.142 \
--ignore-preflight-errors=Swap

–kubernetes-version: 用于指定k8s版本；
–apiserver-advertise-address：用于指定kube-apiserver监听的ip地址,就是 master本机IP地址。
–pod-network-cidr：用于指定Pod的网络范围； 10.244.0.0/16
–service-cidr：用于指定SVC的网络范围；
–image-repository: 指定阿里云镜像仓库地址
```

看到以下信息表示安装成功

```plain
Your Kubernetes control-plane has initialized successfully!
 
To start using your cluster, you need to run the following as a regular user:
 
  mkdir -p $HOME/.kube
  sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
  sudo chown $(id -u):$(id -g) $HOME/.kube/config
 
You should now deploy a pod network to the cluster.
Run "kubectl apply -f [podnetwork].yaml" with one of the options listed at:
  https://kubernetes.io/docs/concepts/cluster-administration/addons/
 
Then you can join any number of worker nodes by running the following on each as root:
 
kubeadm join 192.168.198.140:6443 --token puqie3.du0y1m1dnvhz5k39 \
    --discovery-token-ca-cert-hash sha256:4a4dded9e8a655948a33fa2d8693b9ce8fb98c06c1479720ae02a17d25c127e1 

```

成功后注意最后一个命令，这个join命令可以用来添加节点，不添加的话默认当前master节点同时会被当做一个

node节点加到k8s集群中。

注意保持好kubeadmjoin，后面会用到的。

如果初始化失败，请使用如下代码清除后重新初始化

```plain
 kubeadm reset
```

配置kubectl

```plain
  mkdir -p $HOME/.kube
  sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
  sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

kubernetes出于安全考虑默认情况下无法在master节点上部署pod，于是用下面方法去掉master节点的污点：

```plain
# 1、kubeadm init创建完集群后，当你部署pod时，查看kubectl describe pod会发现问题
3 node(s) had taints that the pod didn't tolerate.
 
# 2、解决方法
kubectl taint nodes --all node-role.kubernetes.io/master-
```



#### 1.3 配置网络插件
##### flannel
flannel.yaml

```plain
---
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: psp.flannel.unprivileged
  annotations:
    seccomp.security.alpha.kubernetes.io/allowedProfileNames: docker/default
    seccomp.security.alpha.kubernetes.io/defaultProfileName: docker/default
    apparmor.security.beta.kubernetes.io/allowedProfileNames: runtime/default
    apparmor.security.beta.kubernetes.io/defaultProfileName: runtime/default
spec:
  privileged: false
  volumes:
  - configMap
  - secret
  - emptyDir
  - hostPath
  allowedHostPaths:
  - pathPrefix: "/etc/cni/net.d"
  - pathPrefix: "/etc/kube-flannel"
  - pathPrefix: "/run/flannel"
  readOnlyRootFilesystem: false
  # Users and groups
  runAsUser:
    rule: RunAsAny
  supplementalGroups:
    rule: RunAsAny
  fsGroup:
    rule: RunAsAny
  # Privilege Escalation
  allowPrivilegeEscalation: false
  defaultAllowPrivilegeEscalation: false
  # Capabilities
  allowedCapabilities: ['NET_ADMIN', 'NET_RAW']
  defaultAddCapabilities: []
  requiredDropCapabilities: []
  # Host namespaces
  hostPID: false
  hostIPC: false
  hostNetwork: true
  hostPorts:
  - min: 0
    max: 65535
  # SELinux
  seLinux:
    # SELinux is unused in CaaSP
    rule: 'RunAsAny'
---
kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: flannel
rules:
- apiGroups: ['extensions']
  resources: ['podsecuritypolicies']
  verbs: ['use']
  resourceNames: ['psp.flannel.unprivileged']
- apiGroups:
  - ""
  resources:
  - pods
  verbs:
  - get
- apiGroups:
  - ""
  resources:
  - nodes
  verbs:
  - list
  - watch
- apiGroups:
  - ""
  resources:
  - nodes/status
  verbs:
  - patch
---
kind: ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: flannel
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: flannel
subjects:
- kind: ServiceAccount
  name: flannel
  namespace: kube-system
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: flannel
  namespace: kube-system
---
kind: ConfigMap
apiVersion: v1
metadata:
  name: kube-flannel-cfg
  namespace: kube-system
  labels:
    tier: node
    app: flannel
data:
  cni-conf.json: |
    {
      "name": "cbr0",
      "cniVersion": "0.3.1",
      "plugins": [
        {
          "type": "flannel",
          "delegate": {
            "hairpinMode": true,
            "isDefaultGateway": true
          }
        },
        {
          "type": "portmap",
          "capabilities": {
            "portMappings": true
          }
        }
      ]
    }
  net-conf.json: |
    {
      "Network": "10.244.0.0/16",
      "Backend": {
        "Type": "vxlan"
      }
    }
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: kube-flannel-ds
  namespace: kube-system
  labels:
    tier: node
    app: flannel
spec:
  selector:
    matchLabels:
      app: flannel
  template:
    metadata:
      labels:
        tier: node
        app: flannel
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/os
                operator: In
                values:
                - linux
      hostNetwork: true
      priorityClassName: system-node-critical
      tolerations:
      - operator: Exists
        effect: NoSchedule
      serviceAccountName: flannel
      initContainers:
      - name: install-cni
        image: registry.cn-hangzhou.aliyuncs.com/alvinos/flanned:v0.13.1-rc1
        command:
        - cp
        args:
        - -f
        - /etc/kube-flannel/cni-conf.json
        - /etc/cni/net.d/10-flannel.conflist
        volumeMounts:
        - name: cni
          mountPath: /etc/cni/net.d
        - name: flannel-cfg
          mountPath: /etc/kube-flannel/
      containers:
      - name: kube-flannel
        image: registry.cn-hangzhou.aliyuncs.com/alvinos/flanned:v0.13.1-rc1
        command:
        - /opt/bin/flanneld
        args:
        - --ip-masq
        - --kube-subnet-mgr
        resources:
          requests:
            cpu: "100m"
            memory: "50Mi"
          limits:
            cpu: "100m"
            memory: "50Mi"
        securityContext:
          privileged: false
          capabilities:
            add: ["NET_ADMIN", "NET_RAW"]
        env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
        volumeMounts:
        - name: run
          mountPath: /run/flannel
        - name: flannel-cfg
          mountPath: /etc/kube-flannel/
      volumes:
      - name: run
        hostPath:
          path: /run/flannel
      - name: cni
        hostPath:
          path: /etc/cni/net.d
      - name: flannel-cfg
        configMap:
          name: kube-flannel-cfg
```

##### calico
calico 3.18搭配1.18版本的k8s



部署

```plain
kubectl apply -f flannel.yaml/calico.yaml
```



查看

```plain
[root@master ~]# kubectl get nodes

NAME     STATUS   ROLES    AGE   VERSION
master   Ready    master   45m   v1.18.1
[root@master ~]# 
[root@master ~]# kubectl get pods -n kube-system
NAME                                       READY   STATUS    RESTARTS   AGE
calico-kube-controllers-6bf5d4676d-wtmg9   1/1     Running   0          5m40s
calico-node-q9zhb                          1/1     Running   0          5m40s
coredns-66bff467f8-4dlkx                   1/1     Running   0          45m
coredns-66bff467f8-ngxl5                   1/1     Running   0          45m
etcd-master                                1/1     Running   0          45m
kube-apiserver-master                      1/1     Running   0          45m
kube-controller-manager-master             1/1     Running   4          45m
kube-proxy-hckxc                           1/1     Running   0          45m
kube-scheduler-master                      1/1     Running   4          45m

```



### **第二部分：存储系统原理**
#### **2.1 为什么需要持久化存储？**
+ **问题场景**：容器文件系统是临时的，Pod 重启后数据丢失**核心概念对比表**：

| 概念 | 作用 | 生命周期管理方 |
| :---: | :---: | :---: |
| **PV (Persistent Volume)持久卷** | 集群级别的存储资源抽象（如 NFS 卷、云硬盘） | 管理员或 StorageClass |
| **PVC (Persistent Volume Claim)持久卷声明** | 用户对存储资源的请求（指定容量、访问模式等）绑定过程：PVC → StorageClass → 动态创建PV → 自动绑定 | 用户 |
| **StorageClass** | 定义存储供应的模板（自动创建 PV） | 集群管理员 |


+ PV、PVC是K8S用来做存储管理的资源对象，它们让存储资源的使用变得_**可控**_，从而保障系统的稳定性、可靠性。StorageClass则是为了减少人工的工作量而去_**自动化创建**_PV的组件。所有Pod使用存储只有一个原则：_**先规划**_ → _**后申请**_ → _**再使用**_。![](https://i-blog.csdnimg.cn/blog_migrate/a9d100bbb5e57eab1a5d12056e501dbc.png)

**参考链接：**[大白话说明白K8S的PV / PVC / StorageClass(理论+实践) - 知乎](https://zhuanlan.zhihu.com/p/655923057)

    - **NFS Provisioner**（PVC 选择到对应的StorageClass后，与其关联的 Provisioner 组件来动态创建 PV 资源。）
        * 控制器：监听PVC创建事件 → 自动创建PV → 绑定到PVC
        * 存储路径自动生成：/data/nfs_share/devops-jenkins-data-pvc-xxx

```bash
# 查看当前集群存储类
kubectl get storageclass
```

#### **2.2 NFS 服务搭建**
```bash
# 在 nfs服务器上执行（非集群节点）
yum install -y nfs-utils
mkdir /data/nfs_share
echo "/data/nfs_share *(rw,sync,no_root_squash,no_subtree_check)" > /etc/exports

#/data/nfs_share：服务器上要共享的目录路径。
# *：允许所有客户端访问（也可指定 IP 或网段，如 192.168.1.0/24）。
# (rw,sync,no_root_squash)：共享选项：
    # rw：客户端具有读写权限​（默认是只读 ro）。
    # sync：数据同步写入磁盘（保证一致性，但性能较低；异步模式为 async）。
    # no_root_squash：客户端的 root 用户在访问时保留 root 权限​（默认会映射为匿名用户，安全风险较高，需谨慎使用）。

systemctl enable --now nfs-server （或者重启）


#验证共享目录
showmount -e localhost
# 预期输出：（如果出现非预期结果，请先根据输出结果自行判断为什么问题）
# /data/nfs_share *
```

##### **在所有K8s节点安装NFS客户端**
```bash
# 在master01、node01、node02上分别执行：
sudo yum install -y nfs-utils

# 验证客户端可用性（在任意节点执行）
showmount -e nfs服务器ip
# 预期输出：（如果出现非预期结果，请先根据输出结果自行判断为什么问题）
# /data/nfs_share *
```

#### **2.3 创建 StorageClass**
```yaml
#安装helm
#https://mirrors.huaweicloud.com/helm/v3.2.0/
#https://blog.csdn.net/weixin_45653474/article/details/143230491
tar -zxvf helm包
cp ./helm /usr/local/bin/helm
helm version

# 3.1 添加Helm仓库
helm repo add nfs-subdir-external-provisioner https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/
helm repo update

# 3.2 创建专用命名空间
kubectl create ns nfs-provisioner

# 3.3 使用Helm部署Provisioner. Provisioner是 Kubernetes 的一个外部存储动态供应器，用于通过现有的 NFS（网络文件系统）服务器为 Kubernetes 动态创建持久卷（Persistent Volume，PV）。它本身并不提供 NFS 服务，而是依赖已有的 NFS 服务器作为存储后端。
helm upgrade --install nfs-provisioner \
  nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
  --namespace nfs-provisioner \
  --set nfs.server=192.168.198.143 \
  --set nfs.path=/data/nfs_share \
  --set image.repository=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/k8s.gcr.io/sig-storage/nfs-subdir-external-provisioner \
  --set image.tag=v4.0.2 \
  --set storageClass.name=nfs-storage \
  --set storageClass.onDelete="retain" \
  --set extraArgs.enableFixPath=true \
  --set storageClass.defaultClass=true

# 关键参数说明：
# nfs.server: NFS服务器IP
# nfs.path: 共享目录路径
# storageClass.name: 存储类名称
# storageClass.defaultClass: 设为默认存储类
# nfs-storageclass.yaml

kubectl get pod -n nfs-provisioner -w
# 预期输出：
# NAME                                                              READY   STATUS    RESTARTS   AGE
# nfs-provisioner-nfs-subdir-external-provisioner-7d88f5d58-xxxxx   1/1     Running   0          30s

kubectl get storageclass
# 确认 nfs-storage 显示为 (default)
```

##### 创建PVC验证自动绑定
jenkins-pvc.yaml如下：

```yaml
# jenkins-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: jenkins-data-pvc
  namespace: default
spec:
  storageClassName: nfs-storage  # 关联StorageClass 必须与已创建的StorageClass名称一致
  accessModes:
    - ReadWriteOnce              # 单节点读写模式
  resources:
    requests:
      storage: 20Gi              # 存储空间大小
```

**关键点解释**：

+ `accessModes` 类型对比：
    - ReadWriteOnce：单节点读写（适合Jenkins）
    - ReadWriteMany：多节点读写（适合GitLab）
+ PVC 绑定过程：用户声明需求 → 系统匹配 PV → 自动创建绑定

```bash
# 应用PVC配置
kubectl apply -f jenkins-pvc.yaml

# 查看PVC状态
kubectl get pvc 
# 预期输出：
# NAME              STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
# jenkins-data-pvc  Bound    pvc-3a8b9d1e-...                           20Gi       RWO            nfs-storage    10s

# 查看自动创建的PV
kubectl get pv
# 预期输出：
# NAME                                       CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS   CLAIM                     STORAGECLASS   AGE
# pvc-3a8b9d1e-...                          20Gi       RWO            Delete           Bound    devops/jenkins-data-pvc   nfs-storage    20s
```

![](images\image-20250301185628602.png)



---

### **第三部分：Jenkins 部署实战**
#### 3.1 deployment与statefulset对比


![](https://i-blog.csdnimg.cn/blog_migrate/ad487159e0a2a6f4808883dd284d44ca.png)

![](https://i-blog.csdnimg.cn/blog_migrate/7367f8070caa8b70d6069219cf3c80bd.png)

**Deployment** 和 **StatefulSet** 核心特性的对比表格：

| **对比维度 ** | **Deployment** | **StatefulSet** |
| :---: | :---: | :---: |
| **适用场景** | **无状态**应用（如 Web 服务器、API 服务） | **有状态**应用（如 MySQL、ZooKeeper、Kafka） |
| **Pod 标识** | 随机名称（如 `web-app-59d8c5f6c4-abcde`） | 固定有序名称（如 `db-0`、`db-1`） |
| **网络标识** | 无固定 IP，通过 Service 负载均衡访问 | 稳定 DNS 名称（`<pod-name>.<service-name>.<namespace>.svc.cluster.local`） |
| **存储** | 共享存储或无持久化存储（所有 Pod 共享同一 PV） | 每个 Pod 有独立的持久化存储（通过 PVC 模板绑定独立 PV） |
| **更新策略** | 滚动更新（无序替换 Pod） | 有序更新（按顺序替换 Pod，如 `db-2` → `db-1` → `db-0`） |
| **扩缩容行为** | 无序扩缩容（Pod 随机创建/删除） | 有序扩缩容（扩容按 `db-0` → `db-1` 顺序；） |
| **删除行为** | 删除 Deployment 时，自动删除所有 Pod | 删除 StatefulSet 时，默认保留 Pod 和存储卷（需手动清理 PVC） |
| **服务发现** | 通过 ClusterIP 或 LoadBalancer Service 访问 | 通过 Headless Service 直接访问特定 Pod（DNS 解析到固定 IP） |
| **数据持久性** | 数据通常不持久化，Pod 重建后数据丢失 | 数据持久化，Pod 重建后仍能挂载原有存储 |
| **典型用例** | 前端应用、无状态微服务 | 数据库、分布式存储系统、消息队列 |


网络查看命令`kubectl get pod -n devops jenkins-0 -o jsonpath='{.metadata.name}.jenkins.devops.svc.cluster.local'`

**volumeClaimTemplates 工作原理**：

+ 自动为每个 Pod 创建 PVC（命名规则：`<模板名>-<statefulset名>-<序号>`）
+ 示例：`jenkins-home-jenkins-0`

---

#### **3.2 StatefulSet 部署解析**
```yaml
# jenkins-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: jenkins
  namespace: default
spec:
  serviceName: jenkins          # 必须定义Headless Service名称
  replicas: 1
  selector:
    matchLabels:
      app: jenkins
  template:
    metadata:
      labels:
        app: jenkins
    spec:
      containers:
      - name: jenkins
        env:
        - name: JAVA_OPTS
          value: "-Dhudson.security.csrf.GlobalCrumbIssuerConfiguration.DISABLE_CSRF_PROTECTION=true"
        image: jenkins/jenkins:lts-jdk11  # 官方镜像（可以替换为阿里云镜像）
        ports:
        - containerPort: 8080
        - containerPort: 50000
        volumeMounts:
        - name: jenkins-home     # 必须与volumeClaimTemplates名称一致
          mountPath: /var/jenkins_home
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
  volumeClaimTemplates:         # StatefulSet核心特性：动态创建PVC
  - metadata:
      name: jenkins-home
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: "nfs-storage"
      resources:
        requests:
          storage: 5Gi

```



---

#### **3.3 服务暴露方案**
##### **Service 的核心功能**
[几张图就把 Kubernetes Service 掰扯清楚了 - k8s-kb - 博客园](https://www.cnblogs.com/k8s/p/14393784.html)

| 类型 | 作用 | 典型场景 |
| :---: | :---: | :---: |
| **ClusterIP** | 为 Pod 提供集群内部访问的虚拟 IP 和 DNS 名称 | 微服务间通信 |
| **NodePort** | 通过节点 IP + 端口暴露服务（范围 30000-32767） | 临时测试环境 |
| **Headless** | 无 ClusterIP，直接返回 Pod IP（用于 StatefulSet 的 DNS 解析） | 数据库集群等有状态服务 |


![](https://img2020.cnblogs.com/blog/1902657/202102/1902657-20210209180416277-174961.png)

##### **1. ClusterIP（默认类型）**
**核心特点**：  
• 分配一个 **集群内部虚拟 IP**，仅限集群内访问（Pod 之间、节点之间）  
• 无法从集群外部直接访问  
• 适用于 **内部服务通信**（如微服务间调用）

**YAML 示例**：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  type: ClusterIP  # 默认可省略
  ports:
  - port: 80       # Service 监听的端口
    targetPort: 80 # 容器实际暴露的端口
  selector:
    app: my-app
```

**访问方式**：  
• 其他 Pod 通过 `http://my-service:80` 访问  
• 通过 `kubectl port-forward` 临时调试

---

##### **2. NodePort**
**核心特点**：  
• 在 ClusterIP 基础上，**在所有节点上开放一个静态端口**（默认 30000-32767）  
• 通过 `节点IP:NodePort` 可从外部访问服务  
• 适用于 **临时测试** 或 **非生产环境暴露服务**

**YAML 示例**：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  type: NodePort
  ports:
  - port: 80
    targetPort: 80
    nodePort: 31000  # 可选指定端口（不指定则自动分配）
  selector:
    app: my-app
```

**访问方式**：  
• 集群内部：`http://my-service:80`  
• 集群外部：`http://任意节点IP:31000`

---

##### **3. LoadBalancer**
**核心特点**：  
• 在 NodePort 基础上，**自动创建云提供商的负载均衡器**（如 AWS ELB、GCP LB）  
• 分配一个 **外部公网 IP** 直接访问服务  
• 适用于 **生产环境对外暴露服务**  
• 需要云厂商支持（本地环境需额外配置 MetalLB 等）

**YAML 示例**：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: my-app
```

**访问方式**：  
• 自动获得的外部 IP：`http://<EXTERNAL-IP>:80`

---

##### **4. ExternalName**
**核心特点**：  
• 将 Service 映射到 **外部 DNS 名称**（通过 CNAME 记录）  
• 不创建任何代理或端口映射  
• 用于 **集群内访问外部服务**（如数据库、第三方 API）

**YAML 示例**：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: external-db
spec:
  type: ExternalName
  externalName: my-database.example.com  # 外部服务的域名
```

**访问方式**：  
• 集群内部通过 `http://external-db` 访问外部服务 `my-database.example.com`

---

###### **对比总结**
| 类型 | 访问范围 | IP 类型 | 典型场景 | 网络层级 |
| --- | --- | --- | --- | --- |
| **ClusterIP** | 集群内部 | 虚拟 IP | 微服务间内部通信 | 4 层 (TCP/UDP) |
| **NodePort** | 外部可访问 | 节点 IP + 端口 | 开发测试、临时暴露服务 | 4 层 |
| **LoadBalancer** | 外部可访问 | 公网 IP | 生产环境暴露服务 | 4 层 |
| **ExternalName** | 集群内部 | DNS 别名 | 集成外部服务（如数据库） | 7 层 (DNS) |


---

###### **补充说明**
• **Ingress**：更高级的 7 层流量管理（HTTP/HTTPS），通常配合 LoadBalancer 使用，支持基于路径/域名的路由  
• **Headless Service**：无 ClusterIP（`clusterIP: None`），直接返回 Pod IP 列表，适用于 StatefulSet  
• **External Traffic Policy**：  
  • `Cluster`（默认）：流量可能被转发到其他节点的 Pod，会丢失客户端源 IP  
  • `Local`：只转发到本节点 Pod，保留客户端源 IP，但需要 Pod 均匀分布在节点上

根据你的需求选择合适的 Service 类型：  
• **测试环境** → NodePort  
• **生产对外暴露** → LoadBalancer + Ingress  
• **内部服务通信** → ClusterIP  
• **访问外部服务** → ExternalName

##### Ingress 的核心功能
[几张图解释明白 Kubernetes Ingress - k8s-kb - 博客园](https://www.cnblogs.com/k8s/p/14395514.html)

![](https://img2020.cnblogs.com/blog/1902657/202102/1902657-20210210194655036-108856525.png)

+ **外部流量入口**：基于 HTTP/HTTPS 协议的路由规则
+ 高级特性：
    - 路径重写 (`nginx.ingress.kubernetes.io/rewrite-target`)
    - 基于域名的虚拟主机
    - TLS 终止

```yaml
# jenkins-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: jenkins-nodeport
spec:
  type: NodePort  # 服务类型为 NodePort，允许通过节点 IP 和端口访问
  ports:
  - port: 7096  # Service 监听的端口（集群内部访问）
    name: web1 
    nodePort: 7096  # 节点上暴露的端口（范围 30000-32767,但是可以修改）
    targetPort: 8080  # 转发到 Pod 的端口（需与 Pod 容器端口一致)
  - port: 50000
    name: web2
    nodePort: 50000
    targetPort: 50000  # 用于Jenkins节点（也称为slave或agent）与Jenkins主服务器（master）之间的通信
  selector:
    app: jenkins # 选择标签为 app=jenkins 的 Pod
```

端口范围问题解决

```yaml
kubernetes默认端口号范围是 30000-32767 ，如果期望值不是这个区间则需要更改。
1、找到配置文件里，一般的在这个文件夹下： /etc/kubernetes/manifests/
2、找到文件名为kube-apiserver.yaml 的文件，也可能是json格式
3、编辑添加配置 service-node-port-range=1024-65535，如下图所示
```

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1757239656387-12f6ba44-cdc9-400b-95b7-e922ad4df0fd.png)

应用配置：

```bash
kubectl apply -f jenkins-statefulset.yaml

kubectl apply -f jenkins-service.yaml
#验证：

kubectl get svc
# 确认NodePort和Ingress规则生效
```

#### 3.4 初始化配置
```bash
# 获取初始管理员密码
kubectl exec jenkins-0 -- cat /var/jenkins_home/secrets/initialAdminPassword

# 安装推荐插件（通过Web界面）
http://<节点IP>:7096
输入初始密码 → 选择 安装推荐插件
```



### 第四部分：课后作业
按照今天讲的内容完成：

1、测试环境、生产环境、工具集群的k8s部署完成

2、jenkins pod部署完成，并能在浏览器上访问

### 


