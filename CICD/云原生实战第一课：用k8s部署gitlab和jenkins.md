### 云原生实战第一次课程教案  

项目：部门调整 需要重新部署一套CICD平台以供我们部门的开发测试运维使用

项目上线：产品提需求--->需求评审---》代码开发 --》 提交测试 --》 编译打包 --》 应用部署（本地开发：dev  test --》 pre --> prod)

**课程主题：多节点 K8s 集群部署 Jenkins（StatefulSet 模式）与生产级存储设计**

![image-20250309184303150](images\image-20250309184303150.png)

---

#### **课程目标**
1. 理解 Kubernetes 存储体系（PV/PVC/StorageClass）
2. 实现 Jenkins 数据持久化与高可用访问
3. k8s服务对外暴露学习
4. 部署Gitlab到k8s集群并且与Jenkins集成

---

### **第一部分：存储系统原理（20分钟）**
#### **1.1 为什么需要持久化存储？**
- **问题场景**：容器文件系统是临时的，Pod 重启后数据丢失

  **核心概念对比表**：

  |                    概念                     |                             作用                             |    生命周期管理方     |
  | :-----------------------------------------: | :----------------------------------------------------------: | :-------------------: |
  |      **PV (Persistent Volume)持久卷**       |         集群级别的存储资源抽象（如 NFS 卷、云硬盘）          | 管理员或 StorageClass |
  | **PVC (Persistent Volume Claim)持久卷声明** | 用户对存储资源的请求（指定容量、访问模式等）绑定过程：PVC → StorageClass → 动态创建PV → 自动绑定 |         用户          |
  |              **StorageClass**               |              定义存储供应的模板（自动创建 PV）               |      集群管理员       |

  PV、PVC是K8S用来做存储管理的资源对象，它们让存储资源的使用变得***可控***，从而保障系统的稳定性、可靠性。StorageClass则是为了减少人工的工作量而去***自动化创建***PV的组件。所有Pod使用存储只有一个原则：***先规划*** → ***后申请*** → ***再使用***。![在这里插入图片描述](https://i-blog.csdnimg.cn/blog_migrate/a9d100bbb5e57eab1a5d12056e501dbc.png)

  - **NFS Provisioner**（PVC 选择到对应的StorageClass后，与其关联的 Provisioner 组件来动态创建 PV 资源。）
    - 控制器：监听PVC创建事件 → 自动创建PV → 绑定到PVC
    - 存储路径自动生成：/data/nfs_share/devops-jenkins-data-pvc-xxx

  **参考链接：**[大白话说明白K8S的PV / PVC / StorageClass(理论+实践) - 知乎](https://zhuanlan.zhihu.com/p/655923057)

```bash
# 查看当前集群存储类
kubectl get storageclass
```

#### **1.2 NFS 服务搭建（10.3.10.16）**
```bash
# 在 10.3.10.16 上执行（非集群节点）
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

##### 	**在所有K8s节点安装NFS客户端**

```bash
# 在master01、node01、node02上分别执行：
sudo yum install -y nfs-utils

# 验证客户端可用性（在任意节点执行）
showmount -e 10.3.10.16
# 预期输出：（如果出现非预期结果，请先根据输出结果自行判断为什么问题）
# /data/nfs_share *
```

#### **1.3 创建 StorageClass**

```yaml
# 3.1 添加Helm仓库
helm repo add nfs-subdir-external-provisioner https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/
helm repo update

# 3.2 创建专用命名空间
kubectl create ns nfs-provisioner

# 3.3 使用Helm部署Provisioner
helm upgrade --install nfs-provisioner \
  nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
  --namespace nfs-provisioner \
  --set nfs.server=10.3.10.16 \
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

#### **创建PVC验证自动绑定**

pvc-yaml如下：

```yaml
# jenkins-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: jenkins-data-pvc
  namespace: devops
spec:
  storageClassName: nfs-storage  # 关联StorageClass 必须与已创建的StorageClass名称一致
  accessModes:
    - ReadWriteOnce              # 单节点读写模式
  resources:
    requests:
      storage: 20Gi              # 存储空间大小
```

**关键点解释**：

- `accessModes` 类型对比：
  - ReadWriteOnce：单节点读写（适合Jenkins）
  - ReadWriteMany：多节点读写（适合GitLab）
- PVC 绑定过程：用户声明需求 → 系统匹配 PV → 自动创建绑定

```bash
# 应用PVC配置
kubectl apply -f jenkins-pvc.yaml

# 查看PVC状态
kubectl get pvc -n devops -w
# 预期输出：
# NAME              STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
# jenkins-data-pvc  Bound    pvc-3a8b9d1e-...                           20Gi       RWO            nfs-storage    10s

# 查看自动创建的PV
kubectl get pv
# 预期输出：
# NAME                                       CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS   CLAIM                     STORAGECLASS   AGE
# pvc-3a8b9d1e-...                          20Gi       RWO            Delete           Bound    devops/jenkins-data-pvc   nfs-storage    20s
```

检查结果：

![image-20250301185628602](images\image-20250301185628602.png)



---



### **第二部分：Jenkins 部署实战（40分钟）**
#### **2.1 创建命名空间**
```bash
kubectl create ns devops
```

#### **2.2 **StatefulSet 核心机制解析

![img](https://i-blog.csdnimg.cn/blog_migrate/ad487159e0a2a6f4808883dd284d44ca.png)

![img](https://i-blog.csdnimg.cn/blog_migrate/7367f8070caa8b70d6069219cf3c80bd.png)

**Deployment** 和 **StatefulSet** 核心特性的对比表格：

| **对比维度 **  |                 **Deployment**                 |                       **StatefulSet**                        |
| :------------: | :--------------------------------------------: | :----------------------------------------------------------: |
|  **适用场景**  |   **无状态**应用（如 Web 服务器、API 服务）    |         **有状态**应用（如 MySQL、ZooKeeper、Kafka）         |
|  **Pod 标识**  |   随机名称（如 `web-app-59d8c5f6c4-abcde`）    |              固定有序名称（如 `db-0`、`db-1`）               |
|  **网络标识**  |      无固定 IP，通过 Service 负载均衡访问      | 稳定 DNS 名称（`<pod-name>.<service-name>.<namespace>.svc.cluster.local`） |
|    **存储**    | 共享存储或无持久化存储（所有 Pod 共享同一 PV） |   每个 Pod 有独立的持久化存储（通过 PVC 模板绑定独立 PV）    |
|  **更新策略**  |            滚动更新（无序替换 Pod）            |   有序更新（按顺序替换 Pod，如 `db-2` → `db-1` → `db-0`）    |
| **扩缩容行为** |        无序扩缩容（Pod 随机创建/删除）         |         有序扩缩容（扩容按 `db-0` → `db-1` 顺序；）          |
|  **删除行为**  |      删除 Deployment 时，自动删除所有 Pod      | 删除 StatefulSet 时，默认保留 Pod 和存储卷（需手动清理 PVC） |
|  **服务发现**  |  通过 ClusterIP 或 LoadBalancer Service 访问   | 通过 Headless Service 直接访问特定 Pod（DNS 解析到固定 IP）  |
| **数据持久性** |      数据通常不持久化，Pod 重建后数据丢失      |            数据持久化，Pod 重建后仍能挂载原有存储            |
|  **典型用例**  |             前端应用、无状态微服务             |               数据库、分布式存储系统、消息队列               |

网络查看命令`kubectl get pod -n devops jenkins-0 -o jsonpath='{.metadata.name}.jenkins.devops.svc.cluster.local'`

**volumeClaimTemplates 工作原理**：

- 自动为每个 Pod 创建 PVC（命名规则：`<模板名>-<statefulset名>-<序号>`）
- 示例：`jenkins-home-jenkins-0`

---

#### **2.3 StatefulSet 部署解析**
```yaml
# jenkins-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: jenkins
  namespace: devops
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
        image: jenkins/jenkins:lts-jdk11  # 官方镜像（可以替换为阿里云镜像）
        ports:
        - containerPort: 8080
        - containerPort: 50000
        volumeMounts:
        - name: jenkins-home     # 必须与volumeClaimTemplates名称一致
          mountPath: /var/jenkins_home
        env:
        - name: JAVA_OPTS
          value: "-Djenkins.install.runSetupWizard=true"  # 开启初始化向导（按需配置）
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
          storage: 20Gi
```



---

#### **2.4 服务暴露方案**

##### **Service 的核心功能**

[几张图就把 Kubernetes Service 掰扯清楚了 - k8s-kb - 博客园](https://www.cnblogs.com/k8s/p/14393784.html)

|     类型      |                             作用                             |        典型场景        |
| :-----------: | :----------------------------------------------------------: | :--------------------: |
| **ClusterIP** |         为 Pod 提供集群内部访问的虚拟 IP 和 DNS 名称         |      微服务间通信      |
| **NodePort**  |        通过节点 IP + 端口暴露服务（范围 30000-32767）        |      临时测试环境      |
| **Headless**  | 无 ClusterIP，直接返回 Pod IP（用于 StatefulSet 的 DNS 解析） | 数据库集群等有状态服务 |

![img](https://img2020.cnblogs.com/blog/1902657/202102/1902657-20210209180416277-174961.png)

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

| 类型             | 访问范围   | IP 类型        | 典型场景                 | 网络层级       |
| ---------------- | ---------- | -------------- | ------------------------ | -------------- |
| **ClusterIP**    | 集群内部   | 虚拟 IP        | 微服务间内部通信         | 4 层 (TCP/UDP) |
| **NodePort**     | 外部可访问 | 节点 IP + 端口 | 开发测试、临时暴露服务   | 4 层           |
| **LoadBalancer** | 外部可访问 | 公网 IP        | 生产环境暴露服务         | 4 层           |
| **ExternalName** | 集群内部   | DNS 别名       | 集成外部服务（如数据库） | 7 层 (DNS)     |

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

![img](https://img2020.cnblogs.com/blog/1902657/202102/1902657-20210210194655036-108856525.png)

- **外部流量入口**：基于 HTTP/HTTPS 协议的路由规则
- 高级特性：
  - 路径重写 (`nginx.ingress.kubernetes.io/rewrite-target`)
  - 基于域名的虚拟主机
  - TLS 终止

```yaml
# jenkins-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: jenkins
  namespace: devops
spec:
  type: NodePort            # 服务类型为 NodePort，允许通过节点 IP 和端口访问
  ports:
  - port: 8080              # Service 监听的端口（集群内部访问）
    targetPort: 8080        # 转发到 Pod 的端口（需与 Pod 容器端口一致）
    nodePort: 30008         # 节点上暴露的端口（范围 30000-32767）
  selector:
    app: jenkins            # 选择标签为 app=jenkins 的 Pod

---
# jenkins-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: jenkins-ingress
  namespace: devops
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /  # 路径重写（将请求路径转发到根）
spec:
  ingressClassName: nginx      # 指定使用的 Ingress 控制器（需提前部署）
  rules:
  - host: jenkins.devops.com   # 域名配置（需解析到 Ingress 控制器 IP） 如果 直接访问 NodePort：未携带 Host 头，请求未被 Ingress 路由到 Jenkins Service，而是被默认后端（Nginx 404）处理。
    http:
      paths:
      - path: /               # 匹配所有路径
        pathType: Prefix      # 前缀匹配
        backend:
          service:
            name: jenkins      # 转发到名为 "jenkins" 的 Service
            port:
              number: 8080    # Service 的端口
```

应用配置：

```bash
kubectl apply -f jenkins-statefulset.yaml

kubectl apply -f jenkins-service.yaml
kubectl apply -f jenkins-ingress.yaml
#验证：

kubectl get svc,ingress -n devops
# 确认NodePort和Ingress规则生效
```

#### 初始化配置

```bash
# 获取初始管理员密码
kubectl exec -n devops jenkins-0 -- cat /var/jenkins_home/secrets/initialAdminPassword

# 安装推荐插件（通过Web界面）
访问 http://jenkins.devops.com 或 http://<节点IP>:30008
输入初始密码 → 选择 "Install suggested plugins"
```



**访问方式对比**：

- NodePort：直接通过节点IP+端口访问（http://10.3.10.101:30008）

- Ingress：通过域名访问（需配置hosts：10.3.10.101 jenkins.devops.com）

  

![image-20250302000804927](images\image-20250302000804927.png)

![image-20250302001744225](images\image-20250302001744225.png)



---

## 第三部分：部署GitLab到K8s集群并与Jenkins集成（70分钟）

### 3.1 GitLab架构设计与存储规划

- 生产级GitLab组件：
  - Web服务（Unicorn/Puma）
  - Sidekiq后台作业
  - Gitaly存储服务
  - PostgreSQL数据库
  - Redis缓存
- 简化部署方案：使用Omnibus官方镜像
- 存储需求分析：
  - 配置文件：ConfigMap
  - 应用数据：PVC（20GB）
  - 仓库数据：PVC（50GB，ReadWriteMany）

### 3.2 创建持久化存储

gitlab-pvc.yaml

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: gitlab-data
  namespace: devops
spec:
  accessModes:
  - ReadWriteMany  # 支持多节点访问
  storageClassName: nfs-storage
  resources:
    requests:
      storage: 50Gi
```

应用配置：
```bash
kubectl apply -f gitlab-pvc.yaml
```

### 3.3创建ConfigMap

#### 1. 创建ConfigMap YAML文件

```yaml
# gitlab-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: gitlab-config
  namespace: devops
data:
  # 基础配置文件（可添加更多自定义配置）
  gitlab.rb: |
    external_url 'http://gitlab.devops.com'
    gitlab_rails['time_zone'] = 'Asia/Shanghai'
    nginx['listen_port'] = 80
    gitlab_rails['initial_root_password'] = "admin123"
    gitlab_rails['gitlab_shell_ssh_port'] = 22
    gitlab_rails['gitlab_shell_git_timeout'] = 800
    gitlab_rails['gitlab_shell_ssh_dir'] = "/var/opt/gitlab/gitlab-shell"
    user['uid'] = 0
    user['gid'] = 0
    web_server['external_users'] = ['nobody']
    postgresql['shared_buffers'] = "256MB"
    redis['maxmemory'] = "512MB"
    sidekiq['max_concurrency'] = 10
    

```

#### 2. 应用ConfigMap配置

```bash
kubectl apply -f gitlab-configmap.yaml
```

#### 3. 验证创建结果

```bash
kubectl get configmap -n devops
# 预期输出：
# NAME           DATA   AGE
# gitlab-config   1      10s

kubectl describe configmap gitlab-config -n devops
# 应显示配置文件内容
```

------

#### 概念解析：什么是ConfigMap？

##### 核心作用

- **配置与镜像解耦**：将应用程序的配置文件从容器镜像中分离
- **动态配置管理**：在不重建镜像的情况下修改应用配置
- **多环境适配**：通过不同ConfigMap实现开发/测试/生产环境配置切换

##### 关键特性对比

|   特性   |      ConfigMap       |         Secret         |
| :------: | :------------------: | :--------------------: |
| 数据类型 |       普通文本       | 加密数据（Base64编码） |
| 典型用途 | 配置文件、命令行参数 |  密码、API密钥、证书   |
|  安全性  |  不建议存储敏感信息  |    专为敏感数据设计    |
| 访问方式 |  环境变量/文件挂载   | 同ConfigMap（需解码）  |

### 3.4 StatefulSet部署GitLab

gitlab-statefulset.yaml

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: gitlab
  namespace: water-devops
spec:
  serviceName: gitlab
  replicas: 1
  selector:
    matchLabels:
      app: gitlab
  template:
    metadata:
      labels:
        app: gitlab
    spec:
      securityContext:
        runAsUser: 0
        fsGroup: 0
        supplementalGroups: [0]
      containers:
      - name: gitlab
        image: gitlab/gitlab-ce:15.0.0-ce.0
        env:
        - name: GITLAB_OMNIBUS_CONFIG
          value: |
            external_url 'http://gitlab.waterdevops.com'
            gitlab_rails['initial_root_password'] = "admin123"
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "3Gi"
            cpu: "1500m"
          limits:
            memory: "6Gi"
            cpu: "3000m"
        readinessProbe:
          httpGet:
            path: /users/sign_in
            port: 80
          initialDelaySeconds: 300
          periodSeconds: 10
        livenessProbe:
          tcpSocket:
            port: 80
          initialDelaySeconds: 300
          periodSeconds: 10
        volumeMounts:
        - name: gitlab-config
          mountPath: /etc/gitlab/gitlab.rb
          subPath: gitlab.rb
        - name: gitlab-data
          mountPath: /var/opt/gitlab
      volumes:
      - name: gitlab-config
        configMap:
          name: gitlab-config
          defaultMode: 0644
      - name: gitlab-data
        persistentVolumeClaim:
          claimName: gitlab-data

```

### 3.4 服务暴露与访问配置

gitlab-service.yaml

```yaml
apiVersion: v1          # 核心API版本，Service属于核心API组
kind: Service           # 资源类型为Service，用于暴露Pod网络
metadata:
  name: gitlab          # Service名称，集群内通过该名称访问
  namespace: devops     # 所属命名空间，限定资源可见范围
spec:
  type: NodePort        # 服务类型，NodePort表示开放节点端口（范围30000-32768）
  ports:
  - name: http          # 端口命名标识（可选）
    port: 80            # Service监听的集群内部端口
    targetPort: 80      # 将流量转发到Pod的80端口
    nodePort: 30080  # 手动指定端口
  selector:
    app: gitlab         # 关联标签为app=gitlab的Pod

---
apiVersion: networking.k8s.io/v1  # Ingress API版本
kind: Ingress                     # 资源类型为Ingress，用于HTTP层路由
metadata:
  name: gitlab-ingress            # Ingress规则名称
  namespace: devops               # 必须与Service同命名空间
  annotations:
    # 关键注解：允许上传大文件（GitLab需要）
    nginx.ingress.kubernetes.io/proxy-body-size: "0"  # 0表示不限制
spec:
  ingressClassName: nginx         # 指定使用nginx类型的Ingress控制器
  rules:
  - host: gitlab.devops.com       # 域名匹配规则
    http:
      paths:
      - path: /                   # URL路径匹配规则（此处匹配所有路径）
        pathType: Prefix          # 路径匹配类型（前缀匹配）
        backend:
          service:
            name: gitlab          # 将流量转发到名为gitlab的Service
            port:
              number: 80          # 目标Service的端口
```

应用配置：
```bash
kubectl apply -f gitlab-service.yaml
kubectl apply -f gitlab-ingress.yaml
```


在 Kubernetes 中，Service 是暴露应用的核心抽象，不同类型的 Service 适用于不同场景。以下是主要 Service 类型的对比说明：

---



### 3.5 初始化GitLab配置

1. 获取初始root密码：**初始密码为statefulset中配置的密码**

2. 访问http://gitlab.devops.com 登录（root/Gitlab@12345）

![image-20250305230603184](images\image-20250305230603184.png)

2. 创建新项目"demo-project"

![image-20250309171902595](images\image-20250309171902595.png)

### 3.6 Jenkins与GitLab集成实战

1. 在Jenkins安装GitLab插件：
   - 管理Jenkins → 插件管理 → 搜索"GitLab Plugin" Generic Webhook Trigger 下载安装

2. 配置GitLab连接：
   - 管理Jenkins → 系统配置 → GitLab配置  配置gitlab的access tokens（点击右上角头像下拉选择Settings）![image-20250307235410865](images\image-20250307235410865.png)

   ![image-20250309171409267](images\image-20250309171409267.png)

   - GitLab主机URL：http://gitlab.devops.com

   ![image-20250307235550426](images\image-20250307235550426.png)

3. 创建Pipeline项目：

   - 新建任务 → Pipeline项目

   ![image-20250307235626827](images\image-20250307235626827.png)

   - 在"Pipeline"部分选择"Pipeline script" 选择hello world

   ```
   pipeline {
       agent any
   
       stages {
           stage('Hello') {
               steps {
                   echo 'Hello World'
               }
           }
       }
   }
   
   ```

   

4. 安装Generic Webhook Trigger插件，重启Jenkins。

5.  选择项目后配置构建触发器，勾选Build when......，已勾选的不需取消，默认即可，下拉点击高级选项。 生成token

![image-20250308000455542](images\image-20250308000455542.png)

1. 配置GitLab Webhook自动触发：

   - 进入GitLab项目 → Settings → Webhooks
   - URL：http://10.3.213.101:30008/job/new_test/
   - Secret Token：在Jenkins项目配置中生成

   ![image-20250308000528326](images\image-20250308000528326.png)

   - 触发事件：Push events

4.7 验证CI流程

1. 本地提交代码到GitLab仓库：
```bash
git clone http://gitlab.devops.com/root/demo-project.git
echo "version 1.0" > README.md
git add . && git commit -m "Initial commit"
git push
```
2. 观察Jenkins自动触发构建：
   - 进入Jenkins控制台查看构建状态
3. 查看构建日志确认成功

---

## 第四部分：课程总结与扩展思考

### **关键知识点**

1. 有状态服务存储的差异化配置
3. CI/CD工具链的集成模式

### 课后作业

1. 创建自己的namespace完整部署一套Jenkins+Gitlab 并且打通二者实现webhook联通
   **(区分自己所在的namespace)** 
1. 试试将将GitLab初始密码改为Secret进行部署
2. 实现Jenkins构建成功后自动打GitLab Tag(进阶)

#### **排错锦囊**

```bash
# 常见问题1：PVC处于Pending状态
kubectl describe pvc jenkins-data-pvc -n devops
# 检查点：NFS服务器是否可达、StorageClass是否存在

# 常见问题2：Ingress无法访问
kubectl describe ingress jenkins-ingress -n devops
kubectl logs -n ingress ingress-nginx-controller-knpff | grep "jenkins"
```

```bash
# 查看GitLab日志
kubectl logs -n devops gitlab-0 -c gitlab

# 验证网络连通性
kubectl exec -it jenkins-0 -n devops -- curl -I http://gitlab.devops.com

# 检查Webhook交付状态
进入GitLab项目 → Settings → Webhooks → 最近交付
```

---

下一课预告：基于Kubernetes构建完整的CI/CD流水线，实现自动化测试、镜像构建与滚动更新！