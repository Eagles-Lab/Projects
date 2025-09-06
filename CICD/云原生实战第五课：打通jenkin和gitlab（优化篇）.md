# 云原生实战第五课：打通jenkin和gitlab（优化篇）
## 课程目标：
1、完成python爬虫项目的构建

2、按照企业级标准完善流水线的编排及发布流程



## 完成python爬虫项目的构建
按照之前的思路，分为如下步骤

1、创建python 爬虫的gitlab仓库（之前已创建）

2、harbor创建一个存放python 爬虫镜像的仓库

3、在jenkin新建一条构建python爬虫项目的流水线，并打通gitlab

4、修改Jenkinsfile文件



Jenkinsfile

```python
def label = "slave-${UUID.randomUUID().toString()}"

podTemplate(label: label, containers: [
  containerTemplate(name: 'python', image: 'python:3.11-alpine', command: 'cat', ttyEnabled: true),
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
    def registryUrl = "192.168.198.32:30002"
    def imageEndpoint = "flask/pythontest"
 
    // 获取 git commit id 作为我们后面制作的docker镜像的tag
    def imageTag = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
 
    // 镜像
    def image = "${registryUrl}/${imageEndpoint}:${imageTag}"
 
    stage('单元测试') {
      echo "1.测试阶段，此步骤略，可以根据需求自己定制"
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
# 第一阶段：构建依赖
FROM python:3.11-alpine AS builder

# 创建运行时用户
RUN addgroup -S appuser && adduser -S appuser -G appuser \
    && mkdir -p /home/appuser/.local \
    && chown -R appuser:appuser /home/appuser

USER appuser
WORKDIR /app
COPY requirements.lock .
RUN pip install --user --no-cache-dir -r requirements.lock \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 第二阶段：运行时
FROM python:3.11-alpine

RUN addgroup -S appuser && adduser -S appuser -G appuser \
    && mkdir -p /home/appuser/.local \
    && chown -R appuser:appuser /home/appuser

# 配置阿里云镜像源
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories \
    && apk update \
    && apk add --no-cache curl \
    && rm -rf /var/cache/apk/*

WORKDIR /app

# 复制依赖（确保路径一致）
COPY --from=builder --chown=appuser:appuser /home/appuser/.local /home/appuser/.local
COPY --chown=appuser:appuser . .

ENV PATH="/home/appuser/.local/bin:$PATH" \
    PYTHONPATH="/app" \
    GUNICORN_WORKERS=4

USER appuser
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s \
  CMD curl -fs http://localhost:5000/health || exit 1

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "wsgi:app"]
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
                 sh "kubectl set image deployment/test test=${image}"
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



```python
def label = "slave-${UUID.randomUUID().toString()}"

podTemplate(label: label, containers: [
  containerTemplate(name: 'python', image: 'python:3.11-alpine', command: 'cat', ttyEnabled: true),
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
    def registryUrl = "192.168.198.32:30002"
    def imageEndpoint = "flask/pythontest"
 
    
    // 获取 git commit id 作为我们后面制作的docker镜像的tag
    def imageTag = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
 
    // 镜像
    def image = "${registryUrl}/${imageEndpoint}:${imageTag}"

    stage('单元测试') {
      echo "1.测试阶段，此步骤略，可以根据需求自己定制"
    }

    stage('构建 Docker 镜像') {
      withCredentials([[$class: 'UsernamePasswordMultiBinding',
        credentialsId: 'docker-auth',
        usernameVariable: 'DOCKER_USER',
        passwordVariable: 'DOCKER_PASSWORD']]) {
          container('docker') {
            echo "3. 构建 Docker 镜像阶段"
            sh """
              docker login ${registryUrl} -u ${DOCKER_USER} -p ${DOCKER_PASSWORD}
	      cd flask-crawler
              docker build -f Dockerfile_success -t ${image} .
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
                 sh "kubectl set image deployment/test test=${image}"
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

构建成功

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756615495860-b536ea25-a9ec-44b2-b2fa-68e4539ff71c.png)

但如果作为企业级cicd还有缺陷

## 企业级流水线发布流程
<font style="color:rgb(51,51,51);">配置</font><font style="color:rgb(51,51,51);"> Jenkins Pipeline</font><font style="color:rgb(51,51,51);">： </font>

<font style="color:rgb(51,51,51);">阶段</font><font style="color:rgb(51,51,51);">1</font><font style="color:rgb(51,51,51);">：代码拉取 </font><font style="color:rgb(51,51,51);">→ </font><font style="color:rgb(51,51,51);">单元测试（</font><font style="color:rgb(51,51,51);">pytest</font><font style="color:rgb(51,51,51);">）</font><font style="color:rgb(51,51,51);">→</font><font style="color:rgb(51,51,51);"> SonarQube </font><font style="color:rgb(51,51,51);">扫描。 </font>

<font style="color:rgb(51,51,51);">阶段</font><font style="color:rgb(51,51,51);">2</font><font style="color:rgb(51,51,51);">：构建镜像（多阶段构建优化镜像体积）</font><font style="color:rgb(51,51,51);">→ </font><font style="color:rgb(51,51,51);">推送⾄</font><font style="color:rgb(51,51,51);"> Harbor </font><font style="color:rgb(51,51,51);">私有仓库。 </font>

<font style="color:rgb(51,51,51);">阶段3：Helm 部署到 K8s（</font>**<font style="color:rgb(51,51,51);">区分 Dev/Prod/Test/Pre 环境</font>**<font style="color:rgb(51,51,51);">）。</font>

<font style="color:rgb(51,51,51);">阶段4：基于 </font>**<font style="color:rgb(51,51,51);">GitLab 分⽀模型</font>**<font style="color:rgb(51,51,51);">（如 master 、 dev 、 feature/* ）配置多分⽀流⽔线，⾃动识别并触发不同分⽀的构建任务。 </font>

<font style="color:rgb(51,51,51);">阶段5：为 master 分⽀设置 </font>**<font style="color:rgb(51,51,51);">保护规则</font>**<font style="color:rgb(51,51,51);">：合并需通过代码审核 + 流⽔线全阶段成功（单元测试、SonarQube 扫描、镜像构建）。</font>

<font style="color:rgb(51,51,51);"></font>

### <font style="color:rgb(51,51,51);">不同分支触发不同的构建任务</font>
如开发分支流水线（dev分支），自动部署到k8s开发环境（namespace：dev）; 生产分支流水线（master分支），自动部署到k8s开发环境（namespace：prod）

之前的Jenkinsfile中其实已经做了不同分支的判断，但是构建用的deployment之前没有在不同的namespace中去创建

```python
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test
  namespace: dev
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
        image: 192.168.198.32:30002/redhat/initcontainer:v1.0
      imagePullSecrets:
      - name: registry-secret

```

```python
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test
  namespace: master
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
        image: 192.168.198.32:30002/redhat/initcontainer:v1.0
      imagePullSecrets:
      - name: registry-secret

```

```python
stage('运行 Kubectl') {
      container('kubectl') {
        script {
            if ("${gitBranch}" == 'origin/master') {
              withCredentials([file(credentialsId: 'kubeconfig-shengchan', variable: 'KUBECONFIG')]) {
                 echo "查看生产 K8S 集群 Pod 列表"
                 sh 'echo "${KUBECONFIG}"'
                 sh 'mkdir -p ~/.kube && /bin/cp "${KUBECONFIG}" ~/.kube/config'
                 sh "kubectl get pods"
                 sh "kubectl set image deployment/test test=${image} -n prod"
              }
            }else if("${gitBranch}" == 'origin/develop'){
              withCredentials([file(credentialsId: 'kubeconfig-ceshi', variable: 'KUBECONFIG')]) {
                 echo "查看测试 K8S 集群 Pod 列表"
                 sh 'mkdir -p ~/.kube && /bin/cp "${KUBECONFIG}" ~/.kube/config'
                 sh "kubectl get pods -n kube-system"
                 sh "kubectl set image deployment test test=${image} -n dev"
              }
            }
        }
      } 
```



### 为master设置保护规则（合并需全阶段流水线构建成功）
gitlab中配置只有流水线执行成功，才能合并

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756617662499-5d727160-fe99-42a2-8d0f-6d117c818856.png)

给流水线在Jenkinsfile中配置给gitlab的执行结果返回，这边采用的是调用gitlab接口的方式，大家可以思考一下别的模式可以怎么做

接口中需要有gitlab token、仓库id以及commit id

获取gitlab token，生成的token需要记录下来，刷新就看不到了

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756618317157-96cffa02-9dae-4976-a52e-98e34407dd21.png)



获取仓库 id

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756617550486-d35d4406-035b-4ab1-bd2d-7ca109be0d2d.png)



获取commit id，接口中需要传哈希值

```python
def commitid = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()
```

完整接口

```python
curl --request POST --header 'PRIVATE-TOKEN: 59HQaqVRGXpcWRybxNGa' 'http://192.168.198.32:1180/api/v4/projects/3/statuses/${commitid}?state=success  成功 
curl --request POST --header 'PRIVATE-TOKEN: 59HQaqVRGXpcWRybxNGa' 'http://192.168.198.32:1180/api/v4/projects/3/statuses/${commitid}?state=failed  失败
```



Jenkinsfile

```python
def label = "slave-${UUID.randomUUID().toString()}"

podTemplate(label: label, containers: [
  containerTemplate(name: 'python', image: 'python:3.11-alpine', command: 'cat', ttyEnabled: true),
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
    def registryUrl = "192.168.198.32:30002"
    def imageEndpoint = "flask/pythontest"
     
    // 获取 git commit id 作为我们后面制作的docker镜像的tag
    def imageTag = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
 
    // 镜像
    def image = "${registryUrl}/${imageEndpoint}:${imageTag}"

    //获取commit-id
    def commitid = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()

    try{
        stage('单元测试') {
          echo "1.测试阶段，此步骤略，可以根据需求自己定制"
        }

        stage('构建 Docker 镜像') {
          withCredentials([[$class: 'UsernamePasswordMultiBinding',
            credentialsId: 'docker-auth',
            usernameVariable: 'DOCKER_USER',
            passwordVariable: 'DOCKER_PASSWORD']]) {
              container('docker') {
                echo "3. 构建 Docker 镜像阶段"
                sh """
                  docker login ${registryUrl} -u ${DOCKER_USER} -p ${DOCKER_PASSWORD}
                  cd flask-crawler
                  docker build -f Dockerfile_success -t ${image} .
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
                     sh "kubectl set image deployment/test test=${image} -n prod"
                  }
                }else if("${gitBranch}" == 'origin/develop'){
                  withCredentials([file(credentialsId: 'kubeconfig-ceshi', variable: 'KUBECONFIG')]) {
                     echo "查看测试 K8S 集群 Pod 列表"
                     sh 'mkdir -p ~/.kube && /bin/cp "${KUBECONFIG}" ~/.kube/config'
                     sh "kubectl get pods -n kube-system"
                     sh "kubectl set image deployment test test=${image} -n dev"
                  }
                }
            }
          } 
        }
        sh "curl --request POST --header 'PRIVATE-TOKEN: 59HQaqVRGXpcWRybxNGa' 'http://192.168.198.32:1180/api/v4/projects/3/statuses/${commitid}?state=success'"  // 构建失败
  } catch (Exception e) {
        sh "curl --request POST --header 'PRIVATE-TOKEN: 59HQaqVRGXpcWRybxNGa' 'http://192.168.198.32:1180/api/v4/projects/3/statuses/${commitid}?state=failed'"  // 构建失败
        error "Build failed"
  }

  }
}

```



触发合并（dev合入master）

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756618808276-c32e91c3-fe22-4b86-9b24-791c72bcb1f5.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754830746235-bdb6de0d-0def-4905-9d2b-93a57b9eda57.png?x-oss-process=image%2Fformat%2Cwebp)

流水线执行失败时

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756619089415-ee7b346e-5af1-4224-afff-a5cc8101ef7d.png)

流水线执行成功时

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756619106204-7c1da183-fa67-4654-a129-6d58c37ec85a.png)



课后作业：

1、完成python爬虫项目的构建

2、完成企业级pipline的构建

3、扩展部分：单元测试、<font style="color:rgb(51,51,51);">SonarQube 扫描</font>





