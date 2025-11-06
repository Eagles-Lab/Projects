[root@master01 ~]# kubectl get nodes -o wide
NAME       STATUS   ROLES           AGE    VERSION   INTERNAL-IP    EXTERNAL-IP   OS-IMAGE                      KERNEL-VERSION                 CONTAINER-RUNTIME
master01   Ready    control-plane   151d   v1.29.2   10.3.209.100   <none>        Rocky Linux 9.4 (Blue Onyx)   5.14.0-427.13.1.el9_4.x86_64   docker://27.2.0


# api_server 是要去访问 etcd (port: 客户端 2379. 整个集群的元数据信息) 
W0720 10:34:15.243112       1 logging.go:59] [core] [Channel #5 SubChannel #6] grpc: addrConn.createTransport failed to connect to {Addr: "127.0.0.1:2379", ServerName: "127.0.0.1:2379", }. Err: connection error: desc = "transport: Error while dialing: dial tcp 127.0.0.1:2379: connect: connection refused"

# 2380是服务端口
## fatal -> 灾难
{"level":"fatal","ts":"2025-07-20T10:40:01.446752Z","caller":"etcdmain/etcd.go:204","msg":"discovery failed","error":"listen tcp 10.3.202.100:2380: bind: cannot assign requested address","stacktrace":"go.etcd.io/etcd/server/v3/etcdmain.startEtcdOrProxyV2\n\tgo.etcd.io/etcd/server/v3/etcdmain/etcd.go:204\ngo.etcd.io/etcd/server/v3/etcdmain.Main\n\tgo.etcd.io/etcd/server/v3/etcdmain/main.go:40\nmain.main\n\tgo.etcd.io/etcd/server/v3/main.go:31\nruntime.main\n\truntime/proc.go:250"}



任务3: LNMP业务异常恢复

- 将`/root/resources/01.nginx.yaml,02.phpfpm.yaml,03.mysql.yaml`等文件中NFS地址指向本集群master01
- 为`nginx.yaml,phpfpm.yaml`等文件添加健康检查机制
- 检查`nginx php-fpm mysql`服务
- 通过`bbs.iproute.cn`访问正常


```shell
## 指向本集群master01 nfs的需求
使用v1版本的yaml文件： kubectl apply -f xxxx

## 为什么需要增加健康检查？ 通过 Pod 的status看着是running 但是业务实际上访问是有问题
## 当加上健康检查后, 判断健康检查是否生效？

nginx-6f844478b4-sqcmm   0/1     Running            0

  Warning  Unhealthy  79s (x5 over 118s)  kubelet            Startup probe failed: HTTP probe failed with statuscode: 404

## phpfpm targetPort 900 -> 9000


## check nginx 
[root@master01 resources]# kubectl get pods -o wide
NAME                     READY   STATUS             RESTARTS        AGE     IP               NODE     NOMINATED NODE   READINESS GATES
mysql-5cbcfd9d85-q24qb   1/1     Running            0               22m     10.244.196.175   node01   <none>           <none>
nginx-6f844478b4-5whnc   1/1     Running            0               38s     10.244.140.127   node02   <none>           <none>
nginx-6f844478b4-hxrtd   1/1     Running            0               50s     10.244.140.126   node02   <none>           <none>
nginx-6f844478b4-pf84b   1/1     Running            3 (5m27s ago)   5m37s   10.244.196.177   node01   <none>           <none>
php-5b8ff558c8-7zgr9     1/1     Running            0               14m     10.244.140.125   node02   <none>           <none>
php-5b8ff558c8-g46sk     1/1     Running            0               14m     10.244.140.124   node02   <none>           <none>
php-5b8ff558c8-x4hr9     1/1     Running            0               14m     10.244.196.173   node01   <none>           <none>



## ingress-controller： svc (LoadBalancer)

[root@master01 resources]# kubectl get svc -A | grep ingress
ingress       ingress-nginx-controller             LoadBalancer   10.10.47.140    <pending>     80:30331/TCP,443:31980/TCP   150d
ingress       ingress-nginx-controller-admission   ClusterIP      10.10.236.175   <none>        443/TCP                      150d

## ingress 资源对象

[root@master01 resources]# kubectl get ingress
NAME            CLASS   HOSTS            ADDRESS   PORTS   AGE
ingress-nginx   nginx   bbs.iproute.cn             80      150d

## pod 
[root@master01 resources]# kubectl get pods -A -o wide | grep ingress
ingress       ingress-nginx-controller-27rlh             1/1     Running            13 (2d23h ago)   150d    10.3.205.102     node02     <none>           <none>
ingress       ingress-nginx-controller-mqdll             1/1     Running            2 (3d ago)       150d    10.3.205.101     node01     <none>           <none>


## 访问方式1:
[root@master01 resources]# curl -I -H "Host: bbs.iproute.cn" 10.3.205.100:30331
HTTP/1.1 200 OK

## 访问方式2:
[root@master01 resources]# grep bbs /etc/hosts
10.3.205.101 bbs.iproute.cn
[root@master01 resources]# curl -I bbs.iproute.cn
HTTP/1.1 200 OK
```


任务1: MySQL变更管理
- 修改新密码为:`123456`
- 访问 `bbs.iproute.cn` 正常

任务2: Redis持久化管理
- 配置文件通过Configmap挂载至 `/usr/local/etc/redis/redis.conf`
- 数据目录通过NFS挂载至 `/data`
- 测试验证
