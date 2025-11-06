任务1: MySQL变更管理
- 修改新密码为:`123456`
- 访问 `bbs.iproute.cn` 正常


```shell

## 这里并不能直接去更新 mysql 的密码，仅仅是在pod第一次创建初始化的时候设置的 root 密码
env:
- name: MARIADB_ROOT_PASSWORD
    value: "123"

## 进入 mysql 容器内
[root@master01 ~]# kubectl get pod  -A | grep mysql
default       mysql-6c6797b497-r98zb
[root@master01 ~]# kubectl exec -it mysql-6c6797b497-r98zb -- /bin/bash
root@mysql-6c6797b497-r98zb:/# mysql -uroot -p123
Welcome to the MariaDB monitor.  Commands end with ; or \g.
Your MariaDB connection id is 47037
Server version: 10.3.39-MariaDB-1:10.3.39+maria~ubu2004 mariadb.org binary distribution

Copyright (c) 2000, 2018, Oracle, MariaDB Corporation Ab and others.

Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.
## root 用户密码更新
MariaDB [(none)]> ALTER USER 'root'@'localhost' IDENTIFIED BY '123456';
Query OK, 0 rows affected (0.000 sec)

MariaDB [(none)]> ALTER USER 'root'@'%' IDENTIFIED BY '123456';
Query OK, 0 rows affected (0.000 sec)

MariaDB [(none)]> FLUSH PRIVILEGES;
Query OK, 0 rows affected (0.000 sec)


## 发现 nginx pod 健康检查失败
[root@master01 ~]# kubectl get pod -A | grep nginx
default       nginx-7885fdbbbb-2mcm5                     0/1     Running            1 (57s ago)     21h
default       nginx-7885fdbbbb-d6cjw                     0/1     Running            1 (55s ago)     21h
default       nginx-7885fdbbbb-g6g8g                     0/1     Running            1 (54s ago)     21h
10.3.202.101 - - [21/Jul/2025:10:40:50 +0000] "GET / HTTP/1.1" 503 4209 "-" "kube-probe/1.29" "-"

## 容器内？ NFS？  NFS 的路径目录有挂载给 POD

NFS 配置： /root/data/nfs/php   -> POD: /usr/local/etc
NFS 应用项目： /root/data/nfs/html   ->  POD: /usr/share/nginx/html

## YAML 这种声明式的方式 >> 命令行

## app 应用日志在哪里？ 配置在哪里？ -> 去研发 -> 看整个代码项目结构（存储的位置）

[root@master01 ~]# ls -l /root/data/nfs/html/data/log/
total 44
-rw-r--r-- 1 www-data tape     17187 Feb 21 09:09 202502_cplog.php
-rw-r--r-- 1 www-data tape      1548 Jul 21 18:39 202507_errorlog.php
-rw-r--r-- 1 www-data www-data     0 Feb 20 09:11 index.htm
-rw-r--r-- 1 www-data tape     17066 Feb 20 10:08 install.log

## 告警 -> 监控 -> 看日志 -> 明确定义到某一行代码报错 -> 自己尝试复现
                    -> 技术支持/SRE -> 研发侧同学

## 错误日志 
<?PHP exit;?>	1753094940	<b>(0) notconnect</b><br><b>PHP:</b>index.php#require(%s):0136 -> forum.php#discuz_application->discuz_application->init():0057 -> source/class/discuz/discuz_application.php#discuz_application->discuz_application->_init_db():0066 -> source/class/discuz/discuz_application.php#discuz_database::discuz_database::init():0444 -> source/class/discuz/discuz_database.php#db_driver_mysqli->db_driver_mysqli->connect():0023 -> source/class/db/db_driver_mysqli.php#db_driver_mysqli->db_driver_mysqli->_dbconnect():0074 -> source/class/db/db_driver_mysqli.php#db_driver_mysqli->db_driver_mysqli->halt():0085 -> source/class/db/db_driver_mysqli.php#break():0222	087936707e83fa1c7c591bcfba36bb39	<b>User:</b> uid=0; IP=10.3.202.101; RIP:10.3.202.101 Request: /


## 应用项目关于 mysql 配置项
[root@master01 ~]# grep -nrw '123' /root/data/nfs/html/* | head -n 5
grep: /root/data/nfs/html/data/ipdata/ipv6wry.dat: binary file matches
/root/data/nfs/html/config/config_global.php:9:$_config['db'][1]['dbpw'] = '123';
/root/data/nfs/html/config/config_ucenter.php:9:define('UC_DBPW', '123');

sed -i 's/123/123456/g' /root/data/nfs/html/config/config_global.php
sed -i 's/123/123456/g' /root/data/nfs/html/config/config_ucenter.php

## 让 php 相关应用重启一下？ 直接删pod（其他还有更好的更新策略 -> php 里能够通过健康检查捕获到 mysql密码变更后没法正常访问）

## 测试验证
[root@master01 ~]# curl -I bbs.iproute.cn
HTTP/1.1 200 OK

```


任务2: Redis持久化管理
- 配置文件通过Configmap挂载至 `/usr/local/etc/redis/redis.conf`
- 数据目录通过NFS挂载至 `/data`
- 测试验证

```shell
## 参考 04.redis_v1.yaml 文件, apply

## Output: mount.nfs: mounting 10.3.202.100:/root/data/nfs/redis/data failed, reason given by server: No such file or directory
mkdir -pv /root/data/nfs/redis/data
# 进入容器写入测试数据
kubectl exec -it $(kubectl get pods -l app=redis -o jsonpath='{.items[0].metadata.name}') -- redis-cli
> SET testkey "persistence_verified"
> SAVE
# 文件持久化
[root@master01 ~]# tree data/nfs/redis/data/
data/nfs/redis/data/
├── appendonlydir
│   ├── appendonly.aof.1.base.rdb
│   ├── appendonly.aof.1.incr.aof
│   └── appendonly.aof.manifest
└── dump.rdb
# 删除 Pod 触发重建后验证数据
kubectl delete pod $(kubectl get pods -l app=redis -o jsonpath='{.items[0].metadata.name}')
kubectl exec $(kubectl get pods -l app=redis -o jsonpath='{.items[0].metadata.name}') -- redis-cli GET testkey
persistence_verified

```

异常问题： master01 节点重启 docker 之后

```shell
##   Warning  Failed     21s               kubelet            Failed to pull image "redis:latest": Error response from daemon: Get "https://registry-1.docker.io/v2/": net/http: request canceled while waiting for connection (Client.Timeout exceeded while awaiting headers)

## master01 & node01 & node02  /etc/docker/daemon.json 里关于 insecure-registries & registry-mirrors 删掉吧（p.iproute.cn:6443服务已经下线）
## 重启 docker & daemon-reload
[root@master01 resources]# systemctl daemon-reload
[root@master01 resources]# systemctl restart docker


[root@master01 ~]# kubectl get nodes
Error from server (Forbidden): nodes is forbidden: User "kubernetes-admin" cannot list resource "nodes" in API group "" at the cluster scope
## Jul 21 19:36:28 master01 cri-dockerd[1130076]: time="2025-07-21T19:36:28+08:00" level=error msg="Error deleting pod kube-system/calico-kube-controllers-558d465845-xh7sd from network {docker 14f017f83f007856d784e497c3ce2a4>


## kubelet -> cri-docker -> docker 

```
