# 实验环境分组

每个Team资源池提供了5台机器： 1 k8s master 节点 + 3 k8s node 节点 + 1 init（刚装好Linux系统的一台虚拟机）

vpn 客户端： http://117.90.218.109:8889/%E5%AE%9E%E7%94%A8%E5%B7%A5%E5%85%B7/anyconnect%E5%AE%A2%E6%88%B7%E7%AB%AF/windows/cisco-secure-client-win-5.0.02075-core-vpn-predeploy-k9.msi

vpn 连接地址：117.90.218.109:30443； ops + cloud + Y2xvdWQ=

连接实验环境组：
    1. 打开 workstation , 文件 -> 连接服务器 
    2. Server： 10.3.33.233 ;  Username: team03@vsphere.local (team03 一定输入为自己的分组号) ； Password： !QAZ2wsx
    3. 无效的安全证书？？ 总是信任.... 打上勾 ， 仍然连接
    4. workstaion 下看到该 teamX 下的虚拟机资源

开始实验前：先把每台机器恢复到最先的（init）快照

# 环境介绍

每台机器登录方式： root + 1

```shell
team01 
    master01 10.3.201.100
    node01 10.3.201.101
    node02 10.3.201.102
    ....

team02 
    master01 10.3.202.100
    node01 10.3.202.101
    ...

+ 各自组的master01节点也充当 NFS 角色
```

K8S集群的故障恢复（ IP地址发生变更后 我们要怎么恢复？ k8s中的相关组件和各组件的协调工作的流程要熟悉 ）
    Calico 网络插件
    LNMP 业务异常（主要变更导致的） 
    MySQL 变更管理 
    数据持久化：当我们的POD重启/ 销毁重建的时候，DB（MySQL Redis） 数据不能丢
    现有集群负载比较高：需要新增 node 节点
    当业务流量突增的时候， 我们POD要能够水平扩缩容 HPA控制器 扩副本？ 垂直扩缩容 VPA ？ 扩 cpu 和 mem
    MySQL高可用部署？ 
    Redis如果进行哨兵/集群模式的高可用部署？
    弹性扩缩容？



任务1: 将每个节点的IP地址更改为自己所属分组的网段IP

异常现象1: INTERNAL-IP 字段是不对的？
异常现象2: [root@master01 ~]# kubectl get nodes
Unable to connect to the server: dial tcp 10.3.201.100:6443: connect: no route to host
异常现象3: 
`Unable to connect to the server: tls: failed to verify certificate: x509: certificate is valid for 10.0.0.1, 10.3.201.100, not 10.3.204.100`

任务2: 解决上述所有异常现象； kubectl get nodes -o wide 命令输出的集群信息是正常的（IP地址是自己的分组IP）


