任务2: 恢复 kube-system 里 calico 组件

```shell

[root@master01 ~]# kubectl get pods -n kube-system | grep calico
calico-kube-controllers-558d465845-4blqv   0/1     CrashLoopBackOff   8 (2m5s ago)      148d
calico-node-4t2zw                          0/1     Init:1/3           0                 8s
calico-node-sggl6                          0/1     Init:1/3           0                 8s
calico-node-tfvhv                          0/1     Init:1/3           0                 8s
calico-typha-5b56944f9b-gnrpr              1/1     Running            1 (18m ago)       148d

calico-node: 每个节点上都会部署，负责网络的转发，数据层面
calico-kube-controllers : master节点上，负责网络控制层面


[root@master01 ~]# kubectl describe pod calico-node-4t2zw  -n kube-system | grep -A10 Events
Events:
  Type     Reason   Age                     From     Message
  ----     ------   ----                    ----     -------
  Warning  BackOff  5m9s (x10989 over 47h)  kubelet  Back-off restarting failed container install-cni in pod calico-node-4t2zw_kube-system(ce84e3b8-a32f-4f5b-86df-0bbdc1c01f46)


Pod 是由一个/多个 container 

calico-node 

- initContainers : 初始化container，一般pod在启动过程中会先等待init_container运行成功
    upgrade-ipam
    install-cni
    mount-bpffs
- containers
    calico-node


要学会找日志？


[root@master01 resources]# kubectl logs -n kube-system calico-node-4t2zw -c install-cni
W0719 11:42:34.766867       1 client_config.go:618] Neither --kubeconfig nor --master was specified.  Using the inClusterConfig.  This might not work.
2025-07-19 11:42:34.777 [ERROR][1] cni-installer/<nil> <nil>: Unable to create token for CNI kubeconfig error=Unauthorized
2025-07-19 11:42:34.777 [FATAL][1] cni-installer/<nil> <nil>: Unable to create token for CNI kubeconfig error=Unauthorized

install-install -> api_server 权限是不是有问题？有没有配置正确？？


[root@master01 resources]# kubectl logs calico-kube-controllers-558d465845-4blqv -n kube-system | grep -i err
2025-07-19 11:45:24.309 [ERROR][1] client.go 295: Error getting cluster information config ClusterInformation="default" error=Get "https://10.0.0.1:443/apis/crd.projectcalico.org/v1/clusterinformations/default": dial tcp 10.0.0.1:443: connect: no route to host
2025-07-19 11:45:24.309 [INFO][1] main.go 138: Failed to initialize datastore error=Get "https://10.0.0.1:443/apis/crd.projectcalico.org/v1/clusterinformations/default": dial tcp 10.0.0.1:443: connect: no route to host


10.0.0.1:443 -> api_server对内的访问地址 
10.3.202.100:6443 -> 对外的访问地址

热加载： 配置更新之后服务不需要重启


# 将 kube-proxy 里的旧IP地址更改为新
kubectl edit cm -n kube-system kube-proxy


# 删除旧 pod 

kubectl delete pod -n kube-system -l k8s-app=kube-proxy --force=true
kubectl delete pod -n kube-system -l k8s-app=calico-node --force=true
kubectl delete pod -n kube-system -l k8s-app=calico-kube-controllers --force=true


# 再去追踪新的日志

[root@master01 resources]# kubectl logs -n kube-system calico-node-4stnd -c install-cni
2025-07-19 11:56:18.810 [ERROR][1] cni-installer/<nil> <nil>: Unable to create token for CNI kubeconfig error=Post "https://10.0.0.1:443/api/v1/namespaces/kube-system/serviceaccounts/calico-cni-plugin/token": tls: failed to verify certificate: x509: certificate is valid for 10.96.0.1, 10.3.202.100, not 10.0.0.1
2025-07-19 11:56:18.812 [FATAL][1] cni-installer/<nil> <nil>: Unable to create token for CNI kubeconfig error=Post "https://10.0.0.1:443/api/v1/namespaces/kube-system/serviceaccounts/calico-cni-plugin/token": tls: failed to verify certificate: x509: certificate is valid for 10.96.0.1, 10.3.202.100, not 10.0.0.1



## 仅重新生成 api_server 的初始化
[root@master01 ~]# kubeadm init phase certs apiserver
I0717 19:02:38.392738 1119172 version.go:256] remote version is much newer: v1.33.3; falling back to: stable-1.29
[certs] Generating "apiserver" certificate and key
[certs] apiserver serving cert is signed for DNS names [kubernetes kubernetes.default kubernetes.default.svc kubernetes.default.svc.cluster.local master01] and IPs [10.96.0.1 10.3.202.100] # SAN 10.96.0.1 10.3.202.100 这两个IP 


### 再重新上生成一个证书

[root@master01 ~]# cat kubeadm_config.yaml
apiVersion: kubeadm.k8s.io/v1beta3
kind: ClusterConfiguration
apiServer:
  certSANs:
    - "10.3.202.100"
    - "10.0.0.1"

[root@master01 ~]# kubeadm init phase certs apiserver --config kubeadm_config.yaml
I0719 20:02:55.309534 2040872 version.go:256] remote version is much newer: v1.33.3; falling back to: stable-1.29
[certs] Generating "apiserver" certificate and key
[certs] apiserver serving cert is signed for DNS names [kubernetes kubernetes.default kubernetes.default.svc kubernetes.default.svc.cluster.local master01] and IPs [10.96.0.1 10.3.202.100 10.0.0.1]

[root@master01 ~]# kubectl logs -n kube-system  calico-kube-controllers-558d465845-nsp27
2025-07-19 12:05:48.772 [ERROR][1] client.go 295: Error getting cluster information config ClusterInformation="default" error=Get "https://10.0.0.1:443/apis/crd.projectcalico.org/v1/clusterinformations/default": dial tcp 10.0.0.1:443: connect: no route to host

## 将 cluster-info cm 旧IP地址转为新IP
[root@master01 ~]# kubectl edit cm cluster-info -n kube-public

## 完全清理calico相关pod
[root@master01 ~]# kubectl delete pod $(kubectl get pods -A  | grep calico | awk '{print $2}') -n kube-system

[root@master01 ~]# kubectl get pods -A  | grep calico
kube-system   calico-kube-controllers-558d465845-xh7sd   1/1     Running            0                 4m37s
kube-system   calico-node-f4ncr                          1/1     Running            0                 4m36s
kube-system   calico-node-h7zl9                          1/1     Running            0                 4m36s
kube-system   calico-node-zg2bb                          1/1     Running            0                 4m36s
kube-system   calico-typha-5b56944f9b-fkbsc              1/1     Running            0                 4m36s
```


任务3: LNMP业务异常恢复

- 将`/root/resources/01.nginx.yaml,02.phpfpm.yaml,03.mysql.yaml`等文件中NFS地址指向本集群master01
- 为`nginx.yaml,phpfpm.yaml`等文件添加健康检查机制
- 检查`nginx php-fpm mysql`服务
- 通过`bbs.iproute.cn`访问正常





