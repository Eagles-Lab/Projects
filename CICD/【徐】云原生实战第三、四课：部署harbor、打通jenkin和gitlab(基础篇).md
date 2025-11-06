### 云原生实战第四课：部署harbor、打通jenkin和gitlab（基础篇）
#### 课程目标
1、部署harbor

2、构建自动化pipeline打通gitlab到jenkins



#### 背景
1、为什么要部署harbor

2、为什么要构建自动化pipeline打通gitlab到jenkins

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1757205617484-2d34cd46-6c2f-4e40-8b42-ced4630995b6.png?x-oss-process=image%2Fformat%2Cwebp)

开发人员往gitlab里提交更新的代码之后，想要发布，需要经历如下步骤。

```plain
1、拉取代码
2、单元测试
3、构建（配置好软件运行环境、下载依赖包、编译等过程，得到可执行的程序）
4、制作镜像
5、编写或更新yaml，使用最新的镜像，完成上线
```



传统的上线方式，上述步骤需要运维人员在单台或多台主机依次执行，流程步骤繁杂、无法可视化，极容易出错，回滚麻烦。

我们引入jenkins中的Pipeline,就是为了把运维人员手动在单个或多个节点的任务(例如代码拉取、单元测试、构建、部署等)连接到一起，相当于建立了一条流水线，每次上线时，只需要点击构建，即执行这条Pipeline流水线，这些任务就会安装提前设定好的样子依次在单台或多台主机执行，并且我们可以在jenkins界面看到整个过程，实现可视化。



### 第一部分：部署harbor
#### 1.1 创建harbor命名空间
后续将Harbor相关的服务都部署在该命名空间中。

```yaml
kubectl create namespace harbor
```

#### 1.2 创建harbor nfs存储
之前nfs以及部署过了，我们这边只要添加一个目录就行了

服务端

```yaml
mkdir  -p  /data/nfs/harbor        #创建共享目录
 
/etc/exports中添加harbor目录 
/data/nfs/harbor *(rw,sync,no_root_squash,no_subtree_check)

 
systemctl restart nfs
showmount  -e localhost                     #检查共享目录信息
```

客户端

```bash
showmount  -e 192.168.198.143 #检查共享目录信息
```

#### 1.3 创建NFSprovisioner
```bash
cat > nfs-provisioner.yaml << EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: nfs-provisioner
  namespace: harbor
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: nfs-provisioner-cr
rules:
 - apiGroups: [""]
   resources: ["persistentvolumes"]
   verbs: ["get", "list", "watch", "create", "delete"]
 - apiGroups: [""]
   resources: ["persistentvolumeclaims"]
   verbs: ["get", "list", "watch", "update"]
 - apiGroups: ["storage.k8s.io"]
   resources: ["storageclasses"]
   verbs: ["get", "list", "watch"]
 - apiGroups: [""]
   resources: ["events"]
   verbs: ["create", "update", "patch"]
 - apiGroups: [""]
   resources: ["services", "endpoints"]
   verbs: ["get"]
 - apiGroups: ["extensions"]
   resources: ["podsecuritypolicies"]
   resourceNames: ["nfs-provisioner"]
   verbs: ["use"]
 
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: run-nfs-provisioner
subjects:
  - kind: ServiceAccount
    name: nfs-provisioner
    namespace: harbor
roleRef:
  kind: ClusterRole
  name: nfs-provisioner-cr
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: nfs-role
  namespace: harbor
rules:
  - apiGroups: [""]
    resources: ["endpoints"]
    verbs: ["get","list","watch","create","update","patch"]
 
---
kind: RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: leader-locking-nfs-provisioner
  namespace: harbor
subjects:
 - kind: ServiceAccount
   name: nfs-provisioner
   namespace: harbor
roleRef:
 kind: Role
 name: nfs-role
 apiGroup: rbac.authorization.k8s.io
 
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nfs-proversitioner
  namespace: harbor
spec:
  selector:
    matchLabels:
      app: nfs-provisioner
  replicas: 1
  strategy:
    type: Recreate
  template:
    metadata:
      labels:
        app: nfs-provisioner
    spec:
      serviceAccount: nfs-provisioner
      containers:
      - name: nfs-provisioner
        image: registry.cn-beijing.aliyuncs.com/mydlq/nfs-subdir-external-provisioner:v4.0.0
        imagePullPolicy: IfNotPresent
        volumeMounts:
        - name: nfs-client-root
          mountPath: /persistentvolumes
        env:
          - name: PROVISIONER_NAME
            value: example.com/nfs
          - name: NFS_SERVER
            value: 192.168.198.143   # NFS服务端地址
          - name: NFS_PATH
            value: /data/nfs/harbor
      volumes:
      - name: nfs-client-root
        nfs:
          server: 192.168.198.143   #  NFS服务端地址
          path: /data/nfs/harbor  # NFS共享目录
EOF
```

```bash
kubectl apply -f nfs-provisioner.yaml
kubectl -n harbor get pod
 
# 显示
NAME                                  READY   STATUS    RESTARTS   AGE
nfs-proversitioner-5c6f96d484-bvb7d   1/1     Running   0          6s
```

#### 1.4 创建存储类
Harbor的database和redis组件是为有状态服务，需要对Harbor数据做持久化存储。

本处基于NFS创建StorageClass存储类，NFS服务器和共享目录为：

·NFS服务器地址：192.168.198.143

·NFS共享目录：/data/nfs/harbor

```yaml
cat > harbor-storageclass.yaml << EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: harbor-storageclass
provisioner: example.com/nfs #指定外部存储供应商，这里的名称要和provisioner配置文件中的环境变量PROVISIONER_NAME保持一致
parameters:
  archiveOnDelete: "false"
 
EOF
```

```yaml
kubectl apply  -f harbor-storageclass.yaml
kubectl -n harbor  get storageclass
 
# 显示
NAME                  PROVISIONER       RECLAIMPOLICY   VOLUMEBINDINGMODE   ALLOWVOLUMEEXPANSION   AGE
harbor-storageclass   example.com/nfs   Delete          Immediate           false                  0s
```

#### 1.5 部署harbor
添加仓库地址

```yaml
helm repo add harbor https://helm.goharbor.io
 
helm repo  list                  # 查看添加的Chart
```

因为需要修改的参数比较多，在命令行直接helminstall比较复杂，我就将Chart包下载到本地，再修改一些配置。这样比较直观，也比较符合实际工作中的业务环境。

```yaml
helm search repo harbor --versions
helm pull harbor/harbor  --version 1.8.2  # 下载Chart包
tar zxvf harbor-1.8.2.tgz   # 解压包
```

```yaml
$ cd harbor    
$ ls
cert  Chart.yaml  conf  LICENSE  README.md  templates  values.yaml
$ vim  values.yaml
expose:
  type: nodePort         # 我这没有Ingress环境，使用NodePort的服务访问方式。   
  tls:
    enabled: false    # 关闭tls安全加密认证（如果开启需要配置证书）
...
externalURL: http://192.168.198.142:30002   # 使用nodePort且关闭tls认证，则此处需要修改为http协议和expose.nodePort.ports.http.nodePort指定的端口号，IP即为kubernetes的节点IP地址
 
# 持久化存储配置部分
persistence:
  enabled: true   # 开启持久化存储
  resourcePolicy: "keep"
  persistentVolumeClaim:        # 定义Harbor各个组件的PVC持久卷部分
    registry:          # registry组件（持久卷）配置部分
      existingClaim: ""
    storageClass: "harbor-storageclass"           # 前面创建的StorageClass，其它组件同样配置
      subPath: ""
      accessMode: ReadWriteMany          # 卷的访问模式，需要修改为ReadWriteMany，允许多个组件读写，否则有的组件无法读取其它组件的数据
      size: 5Gi
    chartmuseum:     # chartmuseum组件（持久卷）配置部分
      existingClaim: ""
      storageClass: "harbor-storageclass"
      subPath: ""
      accessMode: ReadWriteMany
      size: 5Gi
    jobservice:    # 异步任务组件（持久卷）配置部分
      existingClaim: ""
      storageClass: "harbor-storageclass"    #修改，同上
      subPath: ""
      accessMode: ReadWriteMany
      size: 1Gi
    database:        # PostgreSQl数据库组件（持久卷）配置部分
      existingClaim: ""
      storageClass: "harbor-storageclass"
      subPath: ""
      accessMode: ReadWriteMany
      size: 1Gi
    redis:    # Redis缓存组件（持久卷）配置部分
      existingClaim: ""
      storageClass: "harbor-storageclass"
      subPath: ""
      accessMode: ReadWriteMany
      size: 1Gi
    trivy:         # Trity漏洞扫描插件（持久卷）配置部分
      existingClaim: ""
      storageClass: "harbor-storageclass"
      subPath: ""
      accessMode: ReadWriteMany
      size: 5Gi
...
harborAdminPassword: "Harbor12345"   # admin初始密码，不需要修改
...

...
database:
  # if external database is used, set "type" to "external"
  # and fill the connection informations in "external" section
  type: external # 之前部署gitlab时已经创建了pgsql，所以这边可以复用，由internel改为external，之前上面的database的storageclass就没有用了

...
external:
    host: "postgresql.default.svc.cluster.local" # 修改为pgsql的svc地址
    port: "5432"
    username: "lb" 
    password: "13812121100xX$"
    coreDatabase: "registry" 
    notaryServerDatabase: "notary_server"
    notarySignerDatabase: "notary_signer"

同理redis也是一样
redis:
  # if external Redis is used, set "type" to "external"
  # and fill the connection informations in "external" section
  type: external
...
  external:
    # support redis, redis+sentinel
    # addr for redis: <host_redis>:<port_redis>
    # addr for redis+sentinel: <host_sentinel1>:<port_sentinel1>,<host_sentinel2>:<port_sentinel2>,<host_sentinel3>:<port_sentinel3>
    addr: "redis.default.svc.cluster.local:6379"

...
```



可以复用之前部署gitlab的数据库pgsql，但是需要在里面创建一个给harbor用的用户和库

```yaml
创建用户
create user lb with password '13812121100xX$';
创建那三个库并授权给该用户
create database registry owner lb;
create database notary_server owner lb;
create database notary_signer owner lb;
grant all privileges on database  registry to lb;
grant all privileges on database notary_server to lb;
grant all privileges on database notary_signer to lb;
```

```yaml
[root@k8s-tools harbor]# kubectl get pods
NAME                          READY   STATUS    RESTARTS   AGE
gitlab-7c84d466-w82lm         1/1     Running   0          3h25m
jenkins-0                     1/1     Running   1          7h8m
postgresql-59764f94cf-86cmb   1/1     Running   0          5h37m
redis-57bb46757-dpxlb         1/1     Running   0          5h54m
[root@k8s-tools harbor]# kubectl exec -ti postgresql-59764f94cf-86cmb sh
kubectl exec [POD] [COMMAND] is DEPRECATED and will be removed in a future version. Use kubectl kubectl exec [POD] -- [COMMAND] instead.
# su - postgres
postgres@postgresql-59764f94cf-86cmb:~$ psql
psql (10.9 (Ubuntu 10.9-1.pgdg18.04+1))
Type "help" for help.

postgres=# create user lb with password '13812121100xX$';
CREATE ROLE
postgres=# \du
                                   List of roles
 Role name |                         Attributes                         | Member of 
-----------+------------------------------------------------------------+-----------
 gitlab    | Create DB                                                  | {}
 lb        |                                                            | {}
 postgres  | Superuser, Create role, Create DB, Replication, Bypass RLS | {}

postgres=# create database registry owner lb;
CREATE DATABASE
postgres=# create database notary_server owner lb;
CREATE DATABASE
postgres=# create database notary_signer owner lb;
CREATE DATABASE
postgres=# \l
                                 List of databases
       Name        |  Owner   | Encoding | Collate | Ctype |   Access privileges   
-------------------+----------+----------+---------+-------+-----------------------
 gitlab_production | postgres | UTF8     | C       | C     | =Tc/postgres         +
                   |          |          |         |       | postgres=CTc/postgres+
                   |          |          |         |       | gitlab=CTc/postgres
 notary_server     | lb       | UTF8     | C       | C     | 
 notary_signer     | lb       | UTF8     | C       | C     | 
 postgres          | postgres | UTF8     | C       | C     | 
 registry          | lb       | UTF8     | C       | C     | 
 template0         | postgres | UTF8     | C       | C     | =c/postgres          +
                   |          |          |         |       | postgres=CTc/postgres
 template1         | postgres | UTF8     | C       | C     | =c/postgres          +
                   |          |          |         |       | postgres=CTc/postgres
(7 rows)

postgres=# grant all privileges on database  registry to lb;
GRANT
postgres=# grant all privileges on database notary_server to lb;
GRANT
postgres=# grant all privileges on database notary_signer to lb;
GRANT
postgres=# \q
postgres@postgresql-59764f94cf-86cmb:~$ exit
logout
# exit

```

执行helm install 安装harbor

```yaml
 helm install  harbor  .  -n harbor        # 将安装资源部署到harbor命名空间
```

```yaml
[root@k8s-tools harbor]# kubectl get pods -n harbor
NAME                                    READY   STATUS    RESTARTS   AGE
harbor-chartmuseum-5d79f5877d-6gx7b     1/1     Running   0          8m43s
harbor-core-7cfb5d8cf-cmqwx             1/1     Running   0          8m43s
harbor-jobservice-86dc78b569-cj9b7      1/1     Running   2          8m43s
harbor-nginx-764cc8859-s2pwx            1/1     Running   0          8m43s
harbor-notary-server-696c94cbbd-fz4q4   1/1     Running   0          8m43s
harbor-notary-signer-847f5d7f68-k8pck   1/1     Running   0          8m43s
harbor-portal-7b445c4498-zm9kb          1/1     Running   0          8m43s
harbor-registry-57b67488c8-hdcfz        2/2     Running   0          8m43s
harbor-trivy-0                          1/1     Running   0          8m43s
nfs-proversitioner-66d5fd8646-8wc8p     1/1     Running   0          107m

```

#### 1.6 登录harbor ui界面
[http://192.168.198.142:30002/](http://192.168.198.142:30002/)

admin

Harbor12345

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1758441062559-19a880b0-8590-4fa8-ab23-5aac3d57d353.png)

创建一个项目

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1758441114962-fb3931f4-abd4-4865-96bf-038d89cba8a6.png)

#### 1.7 往harbor中推送镜像
配置docker添加對harbor的信任（强调：在所有k8s集群的节点都添加，包括测试、生产、工具集群）

```yaml
# 如果直接登录我们的harbor仓库会报错http: server gave HTTP response to HTTPS client，需要配置insecure-registries
[root@test06 ~]# cat /etc/docker/daemon.json 
{
"exec-opts": ["native.cgroupdriver=systemd"],
"insecure-registries":["192.168.198.142:30002"], 
"registry-mirrors":["xxx"],
"live-restore":true
}
[root@test06 ~]# systemctl restart docker
```

登录（如果是push操作，或者是拉取私有仓库的镜像都需要登录，后面我们需要在测试、生产拉取私有仓库镜像，在工具集群push镜像，所以三套集群都执行登录操作）

```yaml
[root@test06 ~]# docker login -u admin -p Harbor12345 http://192.168.198.142:30002/
WARNING! Using --password via the CLI is insecure. Use --password-stdin.
WARNING! Your password will be stored unencrypted in /root/.docker/config.json.
Configure a credential helper to remove this warning. See
https://docs.docker.com/engine/reference/commandline/login/#credentials-store
 
Login Succeeded
```

从公共镜像源拉取一个镜像，并推送到我们自己的harbor

```yaml
docker pull centos:8
docker images|grep centos
docker tag centos:8 192.168.198.142:30002/online/centos:8
docker push 192.168.198.142:30002/online/centos:8
```

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1758442665055-54c6df61-1e8f-4c48-8bf2-7cc985ecd84b.png)

以后就可以从我们自己的harbor仓库拉取镜像了

```yaml
docker pull 192.168.198.142:30002/online/centos:8
```



### 第二部分：打通gitlab到jenkins
![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1760226730690-c72ef6dc-61ea-442f-b0a4-ca268816de3c.png)

#### 2.1 jenkins的Pipeline有几个核心概念
Node：节点，一个Node 就是一个Jenkins 节点，Master 或者Agent，是执行 Step 的具体运行环境，比如我们之前动态运行的Jenkins Slave 就是一个Node 节点

Stage：阶段，一个Pipeline 可以定义多个Stage，每个Stage 代表一组操作，比如: Build、Test、Deploy, Stage 是一个逻辑分组的概念，可以跨多个Node

stages有如下特点:

所有stages 会按照顺序运行，即当一个stage 完成后，下一个stage 才会开始，只有当所有 stages 成功完成后，该构建任务(Pipeline)才算成功，如果任何一个stage 失败，那么后面的 stages 不会执行，该构建任务(Pipeline)失败

Step: 步骤，Step是最基本的操作单元，可以是打印一句话，也可以是构建一个Docker镜像，由各类Jenkins 插件提供，比如命令:sh 'make'，就相当于我们平时 shell终端中执行 make 命令一样。



#### 2.2 创建jenkins中的pipeline的两种语法
Pipeline 脚本是由 Groovy语言实现的，但是我们泠必要单独去学习Groovy，用到啥查

Pipeline 支持两种语法：Declarative(声明式)和Scripted (脚本式)语法

例：

##### 声明式
```plain
pipeline {
    agent any // 
    stages {
        stage('Build') { 
            steps {
                // 
            }
        }
        stage('Test') { 
            steps {
                // 
            }
        }
        stage('Deploy') { 
            steps {
                // 
            }
        }
    }
}

```

##### 脚本式
```plain
node {  
    stage('Build') { 
        // 
    }
    stage('Test') { 
        // 
    }
    stage('Deploy') { 
        // 
    }
}

```



#### 2.3 Pipeline 也有两种创建方法
pipeline script 和 pipeline script from scm



##### 2.3.1 pipeline script方式（牛刀小试）
主页-》新建任务/job-》输入一个任务名称，如test2-》点击流水线-》点击确定

在Jenkins的 Web UI界面中输入脚本

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754227197745-7f7cdeb9-cb79-455d-bcd6-5d934b7834ad.png)

在最下方的pipeline区域输入如下脚本，然后点击保存。

注意在应用中，一些slave里有特定的环境，我们的构建任务必须在该环境里运行，这就需要我们指定slave运行，如何指定呢?

需要用到我们之前添加slave pod时指定的label标签，我们之前在之前的小节中指定过一个slave pod并将其label设置为xushenglin-test1,这个标签就是我们选中该slave pod的唯一标识

```yaml
node('xushenglin-test1') {
  stage('Clone') {
    echo "1.Clone Stage"
  }
  stage('Test') {
    echo "2.Test Stage"
  }
  stage('Build') {
    echo "3.Build Stage"
  }
  stage('Deploy') {
    echo "4. Deploy Stage"
  }
}
```

点击构建，然后查看console output，可以看到选中了一个agent名为test1-w0crf，而test1-w0crf就是在k8s临时创建的用于构建本次任务的slave pod，构建完毕后会自动删除该slave pod

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754228623206-ee5221be-f9ec-4f14-9b0f-f4f1bdb72911.png)



##### 2.3.2  pipeline script from scm方式（用这种方式创建一条完整的由gitlab到jenkins的go项目的流水线）
上面一步我们了解了如何创建pipeline，如何构建等基本流程，本节我们就创建一个SCM的流水线，然后完成构建后推送到k8s环境里。



###### 2.3.2.1 思路梳理(以一个go程序为例)
我们的大致思路是。以一个go程序为例

一：在gitab里创建一个项目，该项目用来管理go程序，创建完毕后记录该项目的http或ssh链接信息

二：在jenkins里创建一个go的流水线

构建触发器，定义一个随机字符串作为token值，并选择Pipeline script from SCM，在SCM配置好代码仓库的链接信息（注意:不需要填写任何pipeline的代码）

三：在gitlab里配置webhook

在gitlab里配置好webhook执行jenkins的地址，地址里包含在jenkins里生成的token值

四：编写一个名为Jenkinsfile的文件(强调首字母是一个大写的字母，看清楚了)，把pipeline的代码写到里面，然后扔给开发，开发人员会将该文件放到它的项目根目录下

五：go开发人员通过自己的开发机上传go项目代码(该项目根目录下包含一个名为jenkinsfile的文件)到gitlab中的仓库redhat里，然后会按照jenkinsfile的规定触发一整套流程

所以看明白没有，如果是其他项目如python程序，套路也是一样，上面的一、二、三、四、五步走一遍，再创建一套针对python的就可以了。

通过创建一个Jenkinsfile脚本文件放入项目源码库中,然后jenkins配置SCM，点击构建后拉取源代码，jenkins会从源代码/项目根目录下载入Jenkinsfile文件来执行规定的构建(推荐该方式)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754227250982-57d4b157-ae35-4182-b4a5-97242d1634ab.png)



###### 2.3.2.2 在jenkins里创建一个跑go项目的流水线
先看go事例

```yaml
项目之前创建过，项目名为：redhat
 
# 1、项目的SSH方式链接地址
ssh://git@git.k8s.local:30022/root/redhat.git
 
# 2、项目的http方式链接地址
http://git.k8s.local:1180/root/redhat.git
```

在jenkins里创建一个跑go项目的流水线

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754236056413-d222a2bd-d6e1-47a9-a3bb-235217f29f6c.png)



###### 2.3.2.2 构建触发器
![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754920956150-26f913d9-6807-4f04-aef8-89abe26aca05.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754921194654-e89e76d7-628a-408f-bead-3e0faee0bb0a.png)



###### 2.3.2.3 配置用于构建的分支
![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754921270343-d4541d0c-4e26-476e-a631-a38f80c87d97.png)



###### 2.3.2.4 在gitlab中配置webhook
![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754921548517-8f4655dc-aec1-4f32-a511-827e942bda19.png)

点击Add webhook，在屏幕上面会出现一行粉字:Url is blocked: Requests to the local network are not  allowed  则需要进入 GitLab首页，点击下图所示Admin Area->Settings ->NetWork->勾选 Outbound requests，然 后->点击save changes

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754921740005-bf46a6f8-73fc-457e-8f84-783b6042c8c2.png)

点击save changes之后，回到项目的webhooks界面点击测试

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754922422956-4c6e7208-8cb4-4182-9515-278b7a9f6f71.png)

点击Push events后会报一个403错误，<font style="color:rgb(13, 13, 13);">Jenkins默认启用CSRF防护，要求请求携带</font>`<font style="color:rgb(13, 13, 13);background-color:rgba(27, 31, 35, 0.05);">Crumb</font>`<font style="color:rgb(13, 13, 13);">头（防跨站请求伪造令牌）。如果Hook未包含Crumb，会被拦截。</font>需要做三件事禁用csrf跨站防护：

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754922536300-82424db4-6382-49a9-a648-816464f778b1.png)

系统管理->全局安全配置->勾选匿名用户具有可读权限

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754923035440-ad90d549-d500-4e49-9f9a-edb8e1725d36.png)

禁用csrf跨站请求，有两种方式

1、临时，jenkins重启之后失效；系统管理 ->页面底部选择: 脚本命令行:

```python
import jenkins.model.Jenkins
 
def jenkins = Jenkins.instance
 
jenkins.setCrumbIssuer(null)
```

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754923666519-b70fad11-0632-405c-b72c-a2f588337a0e.png)

2、永久

我们可以修改jenkins.yaml文件,为deployment增加一个env，然后重新部署

```python
      env:
      - name: JAVA_OPTS
        value: "-Dhudson.security.csrf.GlobalCrumbIssuerConfiguration.DISABLE_CSRF_PROTECTION=true"
```

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754923812659-619a0555-ea82-4637-afd7-93d9585599d1.png)

系统管理-》插件管理-》安装GitLab插件

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1760255588025-350cdb45-f36d-4136-849d-b9ad552aed0e.png)

安装完毕后重启，在url地址后输入restart，即:[http://192.168.198.32:709/](http://192.168.198.32:709/)restart

然后点击系统管理-》系统配置-》找到gitlab，去掉勾选:Enable authentication for '/project' end-point

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754923902409-bb5617a0-4d60-4144-902d-2de9ff470d1a.png)



然后再次点击test里的Push events，显示如下内容，代表手动触发push 事件成功

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754924065301-6b6d0f7e-e062-4be6-b801-854ce1f1e8ff.png)



###### 2.3.2.5 往gitlab master和devlop分支提交一段go代码
master

```python
# 1、创建go.mod文件：vim go.mod
module golang
 
go 1.17
 
# 2、编写go代码：vim run.go
package main 
 
import ( 
    "fmt"
    "time"
) 
 
func main() { 
    fmt.Println("主分支.....") 
    time.Sleep(1000000 * time.Second) 
}

```



devlop

```yaml
package main 
 
import ( 
    "fmt"
    "time"
) 
 
func main() { 
    fmt.Println("开发分支.....") 
    time.Sleep(1000000 * time.Second) 
}
 
```

上面两次push都会触发jenkins的流水线执行，但是会因为该项目的两个分支下都没有Jenkinsfile文件而执行失败



###### 2.3.2.6 编写Jenkinsfile
脚本式Jenkinsfile模板

```python
node('xushenglin-test1') {
    stage('Clone') {
      echo "1.Clone Stage"
    }
    stage('Test') {
      echo "2.Test Stage"
    }
    stage('Build') {
      echo "3.Build Docker Image Stage"
    }
    stage('Push') {
      echo "4.Push Docker Image Stage"
    }
    stage('YAML') {
      echo "5.Change YAML File Stage"
    }
    stage('Deploy') {
      echo "6.Deploy Stage"
    }
}
```

### 
注意我们在之前定义过一个pod Template，即slave pod的生成模板，该模板里启动pod引用的是一个镜像jenkins/inbound-agent:jdk11，也就是说，如果我们真的按照上面写的流水线来的，node(xushenglin-test1)也是选中用该镜像jenkins/inbound-agent:jdk11启动的一个slave pod来进行构建，如果我们要构建的是go程序，那么该镜像就不适用了，我们需要用一个具有go环境的镜像才可以。如果你真这么做了，看似可以，实则是一个坑。为什么呢?



因为除了go程序之外，你还有可能会构建java，构建python，那么你需要定制一个非常大的镜像，里面有所有你想要的环境，而且还要有qit工具、docker工具、kubectl等工具，能想象到该镜像会变得多大了吧，而且很不灵活。



思考：有没有更好的方式呢?有

就是我们先制作一个个小镜像/或者基于现成的也行

1、一个有go环境的小镜像

2、一个安装有docker的小镜像

3、一个安装有helm工具的小镜像

4、一个安装有kubectl工具的小镜像

然后我们可以删掉之前创建的pod Template

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754925202129-a36e7a25-1895-4a76-9576-68155c354f2d.png)

然后在pipeline的代码里里动态生成pod template，在里面写好要引用的镜像 ，然后在每个stage里调用专门的镜像就可以，我们可以看到pod slave里会启动多个容器。

这么做的好处是，如果我们想构建另外一条用于构建java程序的流水线，那么我们只需要再创建了一个拥有java环境的小镜像就可以，至于2、3、4提到的镜像都是可以复用的

综上，在做好小镜像之后

1、针对java项目，我们就在java项目根目录下创建一个Jenkinsfile文件，在该文件里写入pipeline流水线代码

2、针对go项目，我们就在go项目根目录下创建一个Jenkinsfile文件，在该文件里写入pipeline流水线代码

3、针对go项目，我们就在python项目根目录下创建一个Jenkinsfile文件，在该文件里写入pipeline流水线代码

这三个Jenkinsfile文件涉及到的安装有docker工具的镜像、helm工具的镜像、kubectl工具的镜像都可以复用





创建k8s集群凭证

登录到jenkins里:主页面-》系统管理-》Manage Credentials->Stores scoped to jenkins下点击全局凭据-》点击jenkins-》点击全局凭据-》点击添加凭据



```yaml
cat /root/.kube/config
```

如果测试环境和线上环境是两套集群，可以分开添加





![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754926671523-ad3555a9-5142-4a5a-9268-163d531a9a5b.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754926698724-04ba32d3-52ab-4cbb-a0a9-5ca3005b74f4.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754926685492-08dafd05-777f-4e6f-a63e-cc2738711ecb.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754926361311-bbdc2c16-5140-41c9-80cb-02f0808448ef.png)





在jenkins里创建一个登录harbor仓库的凭证

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754927202966-25b9d29f-477c-4a74-9dbd-e773058a6335.png)

在harbor创建一个存放go镜像的仓库

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754927624822-97ce3342-f69e-4beb-b4d9-84fc9951da4f.png)



因为我们需要在k8s拉取harbor的私有仓库，需要用到账号密码，所以需要创建一个secret

```python
kubectl create secret docker-registry registry-secret --namespace=default \
--docker-server=192.168.198.142:30002 --docker-username=admin  \
--docker-password=Harbor12345
```



创建deployment

```python
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test
  labels:
    app: test
spec:
  replicas: 1
  selector:
    matchLabels:
      app: test
  template:
    metadata:
      labels:
        app: test
    spec:
      containers:
      - name: test
        image: 192.168.198.142:30002/goproject/redhat:v1
      imagePullSecrets:
      - name: registry-secret

```





为该项目创建Jenkinsfile文件并测试

```python
def label = "slave-${UUID.randomUUID().toString()}"
 
podTemplate(label: label, containers: [
  containerTemplate(name: 'golang', image: 'okteto/golang.1.17', command: 'cat', ttyEnabled: true),
  containerTemplate(name: 'docker', image: 'docker:latest', command: 'cat', ttyEnabled: true),
  containerTemplate(name: 'kubectl', image: 'cnych/kubectl', command: 'cat', ttyEnabled: true)
], serviceAccount: 'jenkins', volumes: [
  hostPathVolume(mountPath: '/var/run/docker.sock', hostPath: '/var/run/docker.sock')
]) {
  node(label) {
    def myRepo = checkout scm
    // 获取开发任意git commit -m "xxx"指定的提交信息xxx
    def gitCommit = myRepo.GIT_COMMIT
    // 获取提交的分支
    def gitBranch = myRepo.GIT_BRANCH
    echo "------------>本次构建的分支是：${gitBranch}"
    // 仓库地址
    def registryUrl = "192.168.198.142:30002"
    def imageEndpoint = "goproject/gotest"
 
    // 获取 git commit id 作为我们后面制作的docker镜像的tag
    def imageTag = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
 
    // 镜像
    def image = "${registryUrl}/${imageEndpoint}:${imageTag}"
 
    stage('单元测试') {
      echo "1.测试阶段，此步骤略，可以根据需求自己定制"
    }
    stage('代码编译打包') {
      try {
        container('golang') {
          echo "2.代码编译打包阶段"
          sh """
            export GOPROXY=https://goproxy.cn
            GOOS=linux GOARCH=amd64 go build -v -o egongogo
            """
        }
      } catch (exc) {
        println "构建失败 - ${currentBuild.fullDisplayName}"
        throw(exc)
      }
    }
    stage('构建 Docker 镜像') {
      withCredentials([[$class: 'UsernamePasswordMultiBinding',
        credentialsId: 'docker-auth',
        usernameVariable: 'DOCKER_USER',
        passwordVariable: 'DOCKER_PASSWORD']]) {
          container('docker') {
            echo "3. 构建 Docker 镜像阶段"
sh '''
cat >Dockerfile<<EOF
FROM centos:8
USER root
COPY ./egongogo /opt/
RUN chmod +x /opt/egongogo
CMD /opt/egongogo
EOF'''
            sh """
              docker login ${registryUrl} -u ${DOCKER_USER} -p ${DOCKER_PASSWORD}
              docker build -t ${image} .
              docker push ${image}
              """
          }
      }
    }
    stage('运行 Kubectl') {
      container('kubectl') {
        script {
            if ("${gitBranch}" == 'origin/master') {
              withCredentials([file(credentialsId: 'kubeconfig-shengchan', variable: 'KUBECONFIG')]) {
                 echo "查看生产 K8S 集群 Pod 列表"
                 sh 'echo "${KUBECONFIG}"'
                 sh 'mkdir -p ~/.kube && /bin/cp "${KUBECONFIG}" ~/.kube/config'
                 sh "kubectl get pods"
                 sh "kubectl set image deployment test test=${image}"
              }
            }else if("${gitBranch}" == 'origin/develop'){
              withCredentials([file(credentialsId: 'kubeconfig-ceshi', variable: 'KUBECONFIG')]) {
                 echo "查看测试 K8S 集群 Pod 列表"
                 sh 'mkdir -p ~/.kube && /bin/cp "${KUBECONFIG}" ~/.kube/config'
                 sh "kubectl get pods -n kube-system"
                 sh "kubectl set image deployment test test=${image}"
              }
            }
        }
      } 
    }
  }
}

```



###### 2.3.2.7 点击push之后，自动触发pipeline
![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756310779660-2b60eb5e-c7b4-4fca-8a0a-70a224a68813.png)



### 第三部分：课后作业
1、完成go项目的整个构建

2、思考如果是python项目如何进行构建

3、流水线是否有不完善的地方





