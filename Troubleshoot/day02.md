异常现象1: INTERNAL-IP 字段是不对的？
异常现象2: [root@master01 ~]# kubectl get nodes
Unable to connect to the server: dial tcp 10.3.201.100:6443: connect: no route to host
异常现象3: 
`Unable to connect to the server: tls: failed to verify certificate: x509: certificate is valid for 10.0.0.1, 10.3.201.100, not 10.3.204.100`

任务2: 解决上述所有异常现象； kubectl get nodes -o wide 命令输出的集群信息是正常的（IP地址是自己的分组IP）



```shell

Unable to connect to the server: dial tcp 10.3.201.100:6443: connect: no route to host --> (master) api_server 配置没有更新

master -> 10.3.202.100 

# 更新 k8s master节点相关配置文件，将旧IP地址更新为新IP地址
sed  -i 's/10.3.202/10.3.209/g' /etc/kubernetes/manifests/kube-apiserver.yaml
sed  -i 's/10.3.202/10.3.209/g' /etc/kubernetes/manifests/etcd.yaml
sed  -i 's/10.3.202/10.3.209/g' /etc/kubernetes/super-admin.conf
sed  -i 's/10.3.202/10.3.209/g' /etc/kubernetes/admin.conf
sed  -i 's/10.3.202/10.3.209/g' /etc/kubernetes/scheduler.conf
sed  -i 's/10.3.202/10.3.209/g' /etc/kubernetes/manifests/etcd.yaml
sed  -i 's/10.3.202/10.3.209/g' /etc/kubernetes/kubelet.conf
# 检查 /etc/kubernetes/ 不存在旧的IP地址
[root@master01 ~]# grep -nr  '201.100' /etc/kubernetes/*

# 发现 .kube/config 里还有指向旧 api_server 的ip地址
[root@master01 ~]# ls -l .kube/config
-rw------- 1 root root 5652 Feb 19 10:34 .kube/config
sed  -i 's/10.3.201/10.3.202/g' .kube/config

# 重启 docker 服务和 kubelet 服务
 systemctl restart docker kubelet

# api_server & controller-manager & scheduler 默认安装在 kube-system 命名空间下
[root@master01 ~]# kubectl get pods -n kube-system -o wide | grep 100 

# 去检查 node 节点，仅 kubelet 服务的配置需要更新
sed  -i 's/10.3.201/10.3.202/g' /etc/kubernetes/kubelet.conf


# ca 证书验证失败，我们需要重新生成新的证书
[root@master01 ~]# kubectl get nodes -o wide
# E0717 18:54:19.018747 1117322 memcache.go:265] couldn't get current server API group list: Get "https://10.3.202.100:6443/api?timeout=32s": tls: failed to verify certificate: x509: certificate is valid for 10.0.0.1, 10.3.201.100, not 10.3.202.100

## 备份
[root@master01 ~]# mv /etc/kubernetes/pki/apiserver.crt backup/
[root@master01 ~]# mv /etc/kubernetes/pki/apiserver.key backup/

## 输出 kubeadm init 操作时默认的模版配置文件
## [root@master01 ~]# kubeadm  config print init-defaults

## 仅重新生成 api_server 的初始化
[root@master01 ~]# kubeadm init phase certs apiserver
I0717 19:02:38.392738 1119172 version.go:256] remote version is much newer: v1.33.3; falling back to: stable-1.29
[certs] Generating "apiserver" certificate and key
[certs] apiserver serving cert is signed for DNS names [kubernetes kubernetes.default kubernetes.default.svc kubernetes.default.svc.cluster.local master01] and IPs [10.96.0.1 10.3.202.100]

## 测试验证

[root@master01 ~]# kubectl get nodes -o wide
NAME       STATUS   ROLES           AGE    VERSION   INTERNAL-IP    EXTERNAL-IP   OS-IMAGE                      KERNEL-VERSION                 CONTAINER-RUNTIME
master01   Ready    control-plane   148d   v1.29.2   10.3.202.100   <none>        Rocky Linux 9.4 (Blue Onyx)   5.14.0-427.13.1.el9_4.x86_64   docker://27.2.0
node01     Ready    <none>          148d   v1.29.2   10.3.202.101   <none>        Rocky Linux 9.4 (Blue Onyx)   5.14.0-427.13.1.el9_4.x86_64   docker://27.2.0
node02     Ready    <none>          148d   v1.29.2   10.3.202.102   <none>        Rocky Linux 9.4 (Blue Onyx)   5.14.0-427.13.1.el9_4.x86_64   docker://27.2.0
[root@master01 ~]#


## 还有一种做法处理node节点？？ 先把node节点从集群中踢出去，踢出去之后再加进来。
1. 驱除工作节点 kubectl drain <node>
2. 删除pod kubectl delete pod <node_ip>  (--all-namespaces)
3. 设置为不可调度节点： kubectl uncordon <node>
4. kubeadm join xxxx 

## 工作场景：比如有一台k8s的node发生物理故障（网络经常性抖动 相对于其他节点上的pod 延时会高或者忽高忽低 ｜ cpu ｜ mem ） 
## 优雅下线机器？ 确保pod在其他node上有重新创建新pod 暴力下线（xxx）

## kube-controller 组件？？  检查当前pod/其他api对象的副本数量 是否 跟预期状态一致？ -> kube-scheduler 重新调度 -> kubelet在对应的node节点上创建新的pod

```


异常现象：
1. k8s集群上还有很多异常的pod
副本不符合预期的：
    kube-system   coredns-857d9ff4c9-26lmv                   0/1     Running            234 (5m40s ago)   148d
STATUS是 ： ImagePullBackOff、ImagePullBackOff 都是一些异常的 要怎么处理？？ 
2. kube-system   calico-kube-controllers-558d465845-4blqv   0/1     CrashLoopBackOff   6 (104s ago)      148d
   有个核心组件（k8s的集群网络组件）


```shell

[root@master01 ~]# kubectl get ns -A
NAME              STATUS   AGE
default           Active   148d # 默认命名空间：php mysql redis 业务服务
ingress           Active   147d
kube-node-lease   Active   148d
kube-public       Active   148d
kube-system       Active   148d # 系统命名空间： k8s集群的核心组件
```

任务2: 恢复 kube-system 里 calico 组件

```shell

[root@master01 ~]# kubectl get pods -n kube-system | grep calico
calico-kube-controllers-558d465845-4blqv   0/1     CrashLoopBackOff   8 (2m5s ago)      148d
calico-node-4t2zw                          0/1     Init:1/3           0                 8s
calico-node-sggl6                          0/1     Init:1/3           0                 8s
calico-node-tfvhv                          0/1     Init:1/3           0                 8s
calico-typha-5b56944f9b-gnrpr              1/1     Running            1 (18m ago)       148d

```