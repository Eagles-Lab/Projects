### 云原生实战第二课：jenkins动态主从、gitlab部署
#### 课程目标
1、jenkins的一主多从模式及动态创建slave pod

2、部署gitlab



#### 背景
为什么要有jenkins主从模式：

因为日常构建Jenkins 任务中，会经常出现下面的情况:

+ 自动化测试需要消耗大量的CPU 和内存资源，如果服务器上还有其他的服务，可能会造成卡顿或者宕机;
+ Jenkins 平台项目众多，如果同一时间构建大量的任务，会出现多个任务抢占资源的情况。Jenkins提供了主从模式 (Master-Slave)解决这个问题。我们可以为Jenkins 配置多台slave 从机，当slave 从机和 Jenkins服务建立连接之后，由Jenkins 发指令给指定的slave 从机运行任务，消耗的资源由 slave 从机去承担。



### 第一部分：jenkins主从模式
#### 1.1 主从模式介绍
英文简称为 Master-Slave，基于分而治之、解耦合的核心思想，将一庞大的工作拆分，master主要负责基本管理、提供操作入口，例如流水线的创建与修改等，至于流水线的具体执行则交给slave去做。

#### 1.2 传统jenkins一主多从模式的缺点
传统的jenkins一主多从架构是有缺点的

1、主Master 发生单点故障时，整个流程都不可用了

2、每个Slave 的配置环境不一样，来完成不同语言的编译打包等操作，但是这些差异化的配置导致管理起来非常不方便，维护起来也是比较费劲，

3、资源有浪费，每台Slave可能是物理机或者虚拟机，当 Slave 处于空闲状态时，也不会完全释放掉资源。或者有的Slave 要运行的job 出现排队等待，而有的Slave 处于空闲状态，



#### 1.3 基于jenkins+k8s动态创建slave pod
针对传统jenkins一主多从的缺陷，我们将jenkins-master跑在k8s里提供故障恢复能力，并且配置动态创建jenkins-slave pod来解决上述2、3问题

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1753801806133-a065178a-f562-466e-8798-149740548953.png)

那什么是动态podslave呢？

需要知道：传统的主从，是静态的，会造成镜像余，单个镜像很大

例如针对不同的程序比如java、go

你需要定义一个java的slave镜像，用于构建java环境，为了完成流水线，该镜像里需要有以下工具

1、拉代码：安装git工具

2、测试：代码检测工具

3、编译：java环境

4、打镜像：docker工具

5、推送到k8s：kubectl工具

你还需要定义一个go的slave镜像，用于构建go环境，为了完成流水线，该镜像里需要有以下工具

1、拉代码：安装git工具

2、测试：代码检测工具

3、编译：go环境

4、打镜像：docker工具

5、推送到k8s：kubectl工具

你会发现go的这个slave的镜像与java这个slave镜像需要安装的余部分太多会造成镜像很大没必要

后续步骤安装k8s插件，就是为了动态创建pod，每次构建都会动态产生一个pod在里面运行slave，该slavepod里会启动多个容器用于流水线的不同阶段

#### 1.4 操作步骤
##### 步骤1：安装k8s 插件（用来动态创建slave pod）
我们需要安装 kubernetes 插件，点击 Manage Jenkins ->Manage Plugins ->Available ->Kubernetes 勾选安装即可。

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756052864301-1871527a-fb14-4776-8799-9cd7a22e6911.png)

##### 步骤2：先制作一个用于jenkins链接k8s工具集群的凭据（注意是工具集群，jenkins的podslave肯定是要运行在工具集群里的嘛)
```plain
首先需要生成jenkins所需的k8s密钥
 
在kubectl命令服务器上找到当初配置连接集群时的 config 文件，位置在 ~/.kube/config
 
# 命令
certificate_authority_data=$(awk -F': ' '/certificate-authority-data/{print $2}' ~/.kube/config)
client_certificate_data=$(awk -F': ' '/client-certificate-data/{print $2}' ~/.kube/config)
client_key_data=$(awk -F': ' '/client-key-data/{print $2}' ~/.kube/config)
 
echo "$certificate_authority_data" | base64 -d > ca.crt
echo "$client_certificate_data" | base64 -d > client.crt
echo "$client_key_data" | base64 -d > client.key
 
# 再生成jenkins使用的PKCS12格式的cert.pfx文件，需要设置密码，注意密码后期jenkins需要
openssl pkcs12 -export -out cert.pfx -inkey client.key -in client.crt -certfile ca.crt
Enter Export Password: 在此输入密码
Verifying - Enter Export Password: 在此输入密码
```

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756053240467-8d9495af-474a-461e-ac4e-d9cadd55cc59.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756053259913-91c9c8d1-066d-48a0-919f-f3d574f5aa48.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756053281718-b68cf10a-f83d-4499-8008-695f8dd2e484.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756053625874-20e6b8ce-94d9-4d39-a248-15682ebefc42.png)

##### 步骤3：配置jenkins链接k8s集群
![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1757819946433-6b95be4e-8753-43ea-a42a-d16250c213d1.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1757820391146-2ec48586-7cbb-4aee-903e-752cf75f32de.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1757820464214-eacb02aa-1139-4089-b4d3-8a3305ca67df.png)

配置正确的话点连接测试，会显示链接成功

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756054244152-c6745011-1960-403f-892f-5359dcb484a0.png)填写jenkins的地址，此处可以填写svc地址，因为工具都部署k8s工具集群中

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756054408824-510e3c01-e7e8-4016-8a12-a9e8a85cdd19.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756054437715-b9f4343b-a034-4c60-bb02-8db8596f71c6.png)

##### 步骤4：手动创建一个pod template
配置PodTemplate，本质就是配置JenkinsSlave运行的Pod模板，为了能够让大家快速看到jenkinslave以一个

pod的方式动态启动与销毁的效果，此处我们就先手动创建一个PodTemplate，你需要事先知道的时候，这个Pod Template在后面我们是可以通过流水线代码自定义的，不同的流水线可以定义自己单独的PodTemplate，完全不需要你在jenkins的web页面里手动创建一个固定死了的PodTemplate，我们此处手动创建只是会提前让你体验一

下动态床podslave的效果而已，后期这个手动创建的固定死了的podtemplate都是可以删掉的。

手动创建一个PodTemplate如下图操作，这里尤其注意Labels/标签列表，它非常重要，后面执行Job会通过该值选中，然后我们这里先 jenkins/inbound-agent:jdk11这个镜像，这个镜像是在官方的jnlp镜像基础上定制的，加入了docker、kubectl等一些实用的工具

再次强调：此处我们添加一个podTemplate只是为了用于案例演示（它的配置包括镜像啥的对我们来说都没啥用），后期我们会删掉该podTemplate，然后用pipeline脚本定制podTemplate、自己选择镜像，所以本小节手动创建一个PodTemplate这一小节的所有步骤都只是为了演示，对后续的实际应用均没啥用。

系统配置->节点管理->ConfigureClouds->PodTemplates->添加Pod模板->PodTemplatesdetails

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756057347035-8578ff4f-965e-4004-84f3-c574db4d062e.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756057479717-03e0719a-1752-4d9f-9a28-46a27b089852.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756058981614-495e06e1-ef55-41bf-9fad-23782b0d5ced.png)

知识点补充：docker in docker

```plain
1、docker in docker 是什么？
docker in docker即在docker容器内运行docker指令
通常不建议在docker容器内运行docker，但在有些场景和业务上，比如我们的CICD，如果agent运行在容器里，我们就是需要在该容器内使用docker命令，比如执行docker pull 拉取镜像，以及docker build构建镜像等操作，docker命令都是提交给了docker的守护进程，所以agent里是需要能够访问到docker守护进程的，如何访问呢？通过套接字文件即可，具体做法就是把宿主机中运行的docker服务的套接字文件映射到jenkins agent容器中即可
 
2、如何实现docker in docker
把宿主机中运行的docker服务的套接字文件docker.sock挂载jenkins agent容器中，实现共享宿主机的docker.socket，这就使得在容器中可以使用宿主机上的docker daemon。
如此，我们便可以在容器内部使用docker pull\push\build image\run等命令了（这些命令的执行都是在与宿主机上面的docker daemon通信）
 
3、示例
docker run -it --name docker-daemon --hostname daemon-test --network=host -v /var/run/docker.sock:/var/run/docker.sock -v /usr/bin/docker:/usr/bin/docker -e DOCKER_HOST="unix:///var/run/docker.sock" centos:7 /bin/bash
–network: 指定容器的网络， 启动容器默认使用bridge网络，这里直接使用主机的网络
-e：设置环境变量，这里直接指定使用docker.sock访问docker daemon
-v: 挂载文件，直接将主机的docker.sock挂载至容器内，共享docker daemon；挂载docker命令脚本至容器内，共享docker服务
```

另外，我们在步骤5，启动SlavePod执行测试命令时，需要k8s权限才行，所以我们需要创建一个ServiceAccount

jenkinsAcount.yaml

```plain
apiVersion: v1
kind: ServiceAccount
metadata:
  name: jenkins
  namespace: default
---
kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1beta1
metadata:
  name: jenkins
rules:
  - apiGroups: ["extensions", "apps"]
    resources: ["deployments", "ingresses"]
    verbs: ["create", "delete", "get", "list", "watch", "patch", "update"]
  - apiGroups: [""]
    resources: ["services"]
    verbs: ["create", "delete", "get", "list", "watch", "patch", "update"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["create","delete","get","list","patch","update","watch"]
  - apiGroups: [""]
    resources: ["pods/exec"]
    verbs: ["create","delete","get","list","patch","update","watch"]
  - apiGroups: [""]
    resources: ["pods/log", "events"]
    verbs: ["get","list","watch"]
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRoleBinding
metadata:
  name: jenkins
  namespace: default
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: jenkins
subjects:
  - kind: ServiceAccount
    name: jenkins
    namespace: default
```

然后在SlavePod配置的地方点击下面的高级，添加上对应的ServiceAccount即可：

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756058080039-c2f98344-7750-418a-9062-dd97b7f4552a.png)

##### 步骤5：创建slave pod
jenkins首页->新建任务->输入一个任务名称、选择Freestyleproject类型的任务

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756058685999-8b670ee4-9526-427a-ac19-82e40de630e1.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756058833697-b61f58bd-525a-4c54-aed2-b13d9a074244.png)

然后往下拉，在Build区域选择Execute shell

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756059185262-4acd7b26-44bc-4e9a-9376-5956fa2865a5.png)

填入测试命令，点击保存

```plain
echo "测试 Kubernetes 动态生成 jenkins slave"
echo "==============执行命令==========="
pwd
 
sleep 60
```

然后点击构建，并查看控制台输出

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756059554396-08410957-e9de-4b5c-82a5-9399b170e1f2.png)





### 第二部分：部署gitlab
在工具集群部署gitlab，Gitlab主要涉及到3个应用：Redis、Postgresql、Gitlab 核心程序，

我们这里选择使用的镜像不是官方的，而是Gitlab容器化中使用非常多的一个第三方镜像：sameersbn/gitlab，

基本上和官方保持同步更新，地址：[http://www.damagehead.com/docker-gitlab/](http://www.damagehead.com/docker-gitlab/)

如果我们已经有可使用的Redis或Postgresql服务的话，那么直接配置在Gitlab环境变量中即可，如果没有的话就单独部署，我们这里为了展示gitlab部署的完整性，还是分开部署。

#### 2.1 部署redis
首先部署需要的Redis服务，对应的资源清单文件如下：（gitlab-redis.yaml)

```plain
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: default
  labels:
    name: redis
spec:
  selector:
    matchLabels:
      name: redis
  template:
    metadata:
      name: redis
      labels:
        name: redis
    spec:
      containers:
      - name: redis
        resources:
          limits:
            cpu: 1
            memory: "2Gi"
          requests:
            cpu: 1
            memory: "2048Mi"
        image: sameersbn/redis:4.0.9-2
        imagePullPolicy: IfNotPresent
        ports:
        - name: redis
          containerPort: 6379
        volumeMounts:
        - mountPath: /var/lib/redis
          name: data
        livenessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 30
          timeoutSeconds: 5
        readinessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 30
          timeoutSeconds: 1
      volumes:
      - name: data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: default
  labels:
    name: redis
spec:
  ports:
    - name: redis
      port: 6379
      targetPort: redis
  selector:
    name: redis
```



#### 2.2 部署postgresql
然后是数据库Postgresql，对应的资源清单文件如下：（gitlab-postgresql.yaml)，存储pv、pvc根据自己的需求设置，本例采用hostPath，先在主机创建目录

```plain
mkdir -p /data/postgresql
```

gitlab-postgresql.yaml文件内容如下，存储空间推荐20Gi，但是因为是测试环境设置为10G

```plain
apiVersion: v1
kind: PersistentVolume
metadata:
  name: postgresql-pv
  namespace: default
  labels:
    type: local
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - "ReadWriteOnce"
  hostPath: 
    path: /data/postgresql
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgresql-pvc
  namespace: default
spec:
  accessModes:
  - "ReadWriteOnce"
  resources:
    requests:
      storage: 10Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgresql
  namespace: default
  labels:
    name: postgresql
spec:
  selector:
    matchLabels:
      name: postgresql
  template:
    metadata:
      name: postgresql
      labels:
        name: postgresql
    spec:
      containers:
      - name: postgresql
        resources:
          limits:
            cpu: 4
            memory: "4Gi"
          requests:
            cpu: 2
            memory: "2048Mi"
        image: sameersbn/postgresql:10-2
        imagePullPolicy: IfNotPresent
        env:
        - name: DB_USER
          value: gitlab
        - name: DB_PASS
          value: passw0rd
        - name: DB_NAME
          value: gitlab_production
        - name: DB_EXTENSION
          value: pg_trgm
        - name: USERMAP_UID
          value: "999"
        - name: USERMAP_GID
          value: "999"
        ports:
        - name: postgres
          containerPort: 5432
        volumeMounts:
        - mountPath: /var/lib/postgresql
          name: data
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -h
            - localhost
            - -U
            - postgres
          initialDelaySeconds: 30
          timeoutSeconds: 1
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: postgresql-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: postgresql
  namespace: default
  labels:
    name: postgresql
spec:
  ports:
    - name: postgres
      port: 5432
      targetPort: postgres
  selector:
    name: postgresql
```



#### 2.3 部署gitlab主应用
然后就是我们最核心的Gitlab的主应用，对应的资源清单文件如下：（gitlab.yaml)，存储也使用hostPath，请依据自己的情况填写存储，但是考虑到性能，还是建议用本地存储，可以考虑用localpath的存储类

创建目录

```plain
mkdir -p /data/gitlab
```

yaml内容如下

```plain
apiVersion: v1
kind: PersistentVolume
metadata:
  name: gitlab-pv
  namespace: default
  labels:
    type: local
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - "ReadWriteOnce"
  hostPath: 
    path: /data/gitlab
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: gitlab-pvc
  namespace: default
spec:
  accessModes:
  - "ReadWriteOnce"
  resources:
    requests:
      storage: 10Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gitlab
  namespace: default
  labels:
    name: gitlab
spec:
  selector:
    matchLabels:
      name: gitlab
  template:
    metadata:
      name: gitlab
      labels:
        name: gitlab
    spec:
      initContainers:
      - name: fix-permissions
        image: busybox
        command: ["sh", "-c", "chown -R 1000:1000 /home/git/data"]
        securityContext:
          privileged: true
        volumeMounts:
        - name: data
          mountPath: /home/git/data
      containers:
      - name: gitlab
        resources:
          requests:
            cpu: 2
            memory: "2Gi"
          limits:
            cpu: 4
            memory: "4Gi"
        image: sameersbn/gitlab:12.9.5
        imagePullPolicy: IfNotPresent
        env:
        - name: TZ
          value: Asia/Shanghai
        - name: GITLAB_TIMEZONE
          value: Beijing
        - name: GITLAB_SECRETS_DB_KEY_BASE
          value: long-and-random-alpha-numeric-string
        - name: GITLAB_SECRETS_SECRET_KEY_BASE
          value: long-and-random-alpha-numeric-string
        - name: GITLAB_SECRETS_OTP_KEY_BASE
          value: long-and-random-alpha-numeric-string
        - name: GITLAB_ROOT_PASSWORD
          value: 'lb13812121100'
        - name: GITLAB_ROOT_EMAIL
          value: 3876144474@qq.com
        - name: GITLAB_HOST
          value: git.k8s.local            # 该域名会是你后面从gitlab里拉取项目的地址，需要添加解析才行
        - name: GITLAB_PORT               # 这个端口很重要，与svc对应好
          value: "1180"
        - name: GITLAB_SSH_PORT           # 这个端口很重要，与svc对应好
          value: "30022"
        - name: GITLAB_NOTIFY_ON_BROKEN_BUILDS
          value: "true"
        - name: GITLAB_NOTIFY_PUSHER
          value: "false"
        - name: GITLAB_BACKUP_SCHEDULE
          value: daily
        - name: GITLAB_BACKUP_TIME
          value: 01:00
        - name: DB_TYPE
          value: postgres
        - name: DB_HOST
          value: postgresql
        - name: DB_PORT
          value: "5432"
        - name: DB_USER
          value: gitlab
        - name: DB_PASS
          value: passw0rd
        - name: DB_NAME
          value: gitlab_production
        - name: REDIS_HOST
          value: redis
        - name: REDIS_PORT
          value: "6379"
        ports:
        - name: http
          containerPort: 80
        - name: ssh
          containerPort: 22
        volumeMounts:
        - mountPath: /home/git/data
          name: data
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 60
          timeoutSeconds: 1
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: gitlab-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: gitlab
  namespace: default
  labels:
    name: gitlab
spec:
  type: NodePort
  ports:
    - name: http
      port: 80
      targetPort: http
      nodePort: 1180
    - name: ssh
      port: 22
      targetPort: ssh
      nodePort: 30022
  selector:
    name: gitlab

```

查看

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1757832029729-c26d7489-a612-45c0-846d-7c4e9f11fa80.png)

强调：gitlab相关信息

```plain
关于gitlab.yaml中的一些环境变量的设置
        - name: GITLAB_ROOT_PASSWORD
          value: 'lb13812121100'
        - name: GITLAB_ROOT_EMAIL
          value: 3876144474@qq.com
        - name: GITLAB_HOST
          value: git.k8s.local
        - name: GITLAB_PORT
          value: "1180"
        - name: GITLAB_SSH_PORT
          value: "30022"
 
# 1、账号
账号名：root
密码为：lb13812121100
 
# 2、svc采用nodePort
web访问端口固定为80
SSH端口固定为30022
 
# 3、结合GITLAB_HOST：git.k8s.local
gitlab的web访问地址为：
    http://git.k8s.local:1180
 
gitlab的ssh访问地址为
    git.k8s.local:30022
 
# 4、GITLAB_HOST：git.k8s.local用来访问gitlab的主机，我们设置为域名，需要为访问者添加指向该域名的地址解析
因为我们的svc采用的是nodeport，并且端口固定，所以搭配一个k8s节点的ip地址就可以访问到
所以我们选取gitlab所在k8s集群中的任意一个节点的ip地址，我们就一个节点，地址为172.16.10.16
所以我们让git.k8s.local解析到该地址就可以
 
需要访问gitlab的有哪些，就在哪里添加解析
    1、一个是k8s的工具集群，里面安装有jenkins需要访问gitlab
    2、另外一个是开发机
    3、需要访问gitlab的web界面的用户
```



添加解析

```plain
# 1、添加自定义解析
[root@k8s-tools ~]# kubectl  -n kube-system edit cm coredns
apiVersion: v1
data:
  Corefile: |
    .:53 {
        errors
        health {
           lameduck 5s
        }
        ready
        hosts { # 添加自定义解析
          192.168.198.142 git.k8s.local
          fallthrough
        }
        kubernetes cluster.local in-addr.arpa ip6.arpa {
           pods insecure
           fallthrough in-addr.arpa ip6.arpa
           ttl 30
        }
        prometheus :9153
        forward . /etc/resolv.conf
        cache 30
        loop
        reload
        loadbalance
    }
kind: ConfigMap
metadata:
  creationTimestamp: "2025-09-07T07:29:31Z"
  managedFields:
  - apiVersion: v1
    fieldsType: FieldsV1
    fieldsV1:
      f:data: {}
    manager: kubeadm
    operation: Update
    time: "2025-09-07T07:29:31Z"
  - apiVersion: v1
    fieldsType: FieldsV1
    fieldsV1:
      f:data:
        f:Corefile: {}
    manager: kubectl
    operation: Update
    time: "2025-09-14T06:54:49Z"
  name: coredns
  namespace: kube-system
  resourceVersion: "64928"
  selfLink: /api/v1/namespaces/kube-system/configmaps/coredns
  uid: b8e14324-5297-4b73-8b0a-7fe16e1e19b2

 
# 2、重启coredns
kubectl  -n kube-system scale deployment coredns --replicas=0
kubectl  -n kube-system scale deployment coredns --replicas=2
 
# 3、测试
[root@test06 ~]# cat test.yaml 
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: test
  name: test
spec:
  replicas: 1
  selector:
    matchLabels:
      app: test
  strategy: {}
  template:
    metadata:
      labels:
        app: test
    spec:
      containers:
      - image: centos:7
        imagePullPolicy: IfNotPresent
        name: test
        command: ["sh","-c","tail -f /dev/null"]
[root@k8s-tools ~]# kubectl apply -f test.yaml
[root@k8s-tools ~]# kubectl exec -it test-75bf4b886f-5j6d2 bash
kubectl exec [POD] [COMMAND] is DEPRECATED and will be removed in a future version. Use kubectl kubectl exec [POD] -- [COMMAND] instead.
[root@test-75bf4b886f-5j6d2 /]# ping git.k8s.local
PING git.k8s.local (192.168.198.142) 56(84) bytes of data.
64 bytes from git.k8s.local (192.168.198.142): icmp_seq=1 ttl=64 time=0.039 ms
64 bytes from git.k8s.local (192.168.198.142): icmp_seq=2 ttl=64 time=0.087 ms
64 bytes from git.k8s.local (192.168.198.142): icmp_seq=3 ttl=64 time=0.064 ms
^C
--- git.k8s.local ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2027ms
rtt min/avg/max/mdev = 0.039/0.063/0.087/0.020 ms

```

在开发机上添加解析

```plain
echo "192.168.198.142 git.k8s.local" >> /etc/hosts
```

在要访问gitlab的web界面进行操作的主机添加hosts文件解析，或者干脆用ip地址192.168.198.142访问也行 比如我们要在windows主机以域名的方式访问gitlab的webui，那么配置HOSTS解析

```plain
# 编辑文件，路径如下
C:\Windows\System32\drivers\etc\HOSTS
 
# 
添加解析
192.168.198.142 git.k8s.local
```

#### 2.4 登录gitlab创建项目
![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1757837158634-8563abb4-3b60-48d2-b2d7-df26241d3ccd.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1757837221387-f6b9de96-1f78-412d-9c9a-1ac89b145ff6.png)

在开发机制作密钥对

```plain
[root@localhost ~]# ssh-keygen
Generating public/private rsa key pair.
Enter file in which to save the key (/root/.ssh/id_rsa): 
Created directory '/root/.ssh'.
Enter passphrase (empty for no passphrase): 
Enter same passphrase again: 
Your identification has been saved in /root/.ssh/id_rsa.
Your public key has been saved in /root/.ssh/id_rsa.pub.
The key fingerprint is:
SHA256:gwWl4mlPm/xvBxAAUPeTTPj1WXWbvUcyy0PyX+p/NiI root@localhost.localdomain
The key's randomart image is:
+---[RSA 2048]----+
|  .oo.++o      .o|
|     ..*...   . =|
|    . ..*o ..o+oo|
|   . o oo.  o= =.|
|    + o S.    =.o|
|   . + o ..    +o|
|      =    .  . .|
|       .  .E.o .o|
|        .o... oo+|
+----[SHA256]-----+
[root@localhost ~]# cat /root/.ssh/id_rsa.pub 
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDfkXE3/KZWPSsLi7bpuoybEYWm1kgeYIn3+W8zPwZntdGkBisyaQ+yQK8yEL8rcxr7/8ztOdX2uw7Iz6YYCMvlC68YnpvU1CvZfSHd4mG2Uz68sl0VRS898m4Tj7zKg1jwX/3CULyP8PPTQQYaFoibJoylVPX5lFIcu7cyFoUd0q3JVeM0rpEtja1qvtjGrqvyUQig6aTyaeIE05kEzyTkBACIEEtDpRUSXaBnpRx2VjJ7Kzv95a1kjJO0RWq5vYgu++bUa0Dj1fuwICau8pjFPWYCIMp8+FAlRoFhe9wd6uvexlf099X26gE8+2rHHfVOnpTf6v41WGtoI/ky+52v root@localhost.localdomain

```

复制密钥到gitlab

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1757837897189-fe9e87da-0e9c-4915-a5d1-4dd8b18662a7.png)

开发机模拟更新代码

```plain
yum install git -y
git clone ssh://git@git.k8s.local:30022/root/redhat.git/redhat.git

# 配置全局用户名和邮箱（提交时标识身份）
git config --global user.name "root"
git config --global user.email "3876144474@qq.com"

# 关联本地与远程仓库
git remote add origin ssh://git@git.k8s.local:30022/root/redhat.git/redhat.git
git remote -v

 
[root@localhost redhat]# cat go.mod 
module golang

go 1.17


[root@localhost redhat]# cat run.go 
package main

import (
    "fmt"
    "time"
)

func main() {
    fmt.Println("主分支。。。")
    time.sleep(10000000 * time.Second)
}

# 工作区开发—>将修改后的文件添加到暂存区—>将暂存区的文件记录到版本库
# git的三个区域
# 工作区： 处理工作的区域
# 暂存区： 临时存放的区域
# 本地git仓库： 最终的存放区域

# 添加文件到暂存区
git add .
# 添加文件到本地仓库
git commit -m "第一次提交master"
# 推送本地仓库到远程仓库
git push origin master

#创建develop分支
[root@localhost redhat]# git checkout -b develop
切换到一个新分支 'develop'
[root@localhost redhat]# git branch
* develop
  master
[root@localhost redhat]# ls
go.mod  run.go

[root@localhost redhat]# cat run.go 
package main

import (
    "fmt"
    "time"
)

func main() {
    fmt.Println("开发分支。。。")
    time.sleep(10000000 * time.Second)
}

[root@localhost redhat]# git add .
[root@localhost redhat]# git commit -m "第一次提交开发分支"
[develop dd6a6a0] 第一次提交开发分支
 1 file changed, 1 insertion(+), 1 deletion(-)
[root@localhost redhat]# git push origin develop
Counting objects: 5, done.
Compressing objects: 100% (3/3), done.
Writing objects: 100% (3/3), 333 bytes | 0 bytes/s, done.
Total 3 (delta 1), reused 0 (delta 0)
remote: 
remote: To create a merge request for develop, visit:
remote:   http://git.k8s.local:1180/root/redhat/-/merge_requests/new?merge_request%5Bsource_branch%5D=develop
remote: 
To ssh://git@git.k8s.local:30022/root/redhat.git
 * [new branch]      develop -> develop

```



### 第三部分：课后作业
1、完成jenkins slave pod的创建

2、部署gitlab，并且创建一个project，并进行代码的提交、分支创建 

