### 云原生实战第五课：打通jenkin和gitlab（优化篇）
#### 课程目标：
1、优化流水线的发布流程

2、仿照之前的go项目完成一个python爬虫项目的构建



#### 背景：
整条流水线目前已全部打通，但是光打通是不够的，对于企业级环境来说仍然有很多问题。

问题一：代码提交之后没有进行单元测试、<font style="color:rgb(51,51,51);">SonarQube 扫描就直接进行了发布部署</font>

<font style="color:rgb(51,51,51);">问题二：线上环境的代码发布之前没有进行发布确认，一键推送之后就直接发布到线上环境中了风险较高</font>

<font style="color:rgb(51,51,51);">问题三：没有回滚功能，新版本发布如果出现问题，无法及时回滚老版本进行止损</font>

<font style="color:rgb(51,51,51);">问题四：develop分支(测试环境代码)合并如master分支(线上环境分支)没有进行合并校验</font>



### 第一部分：优化流水线的发布流程
#### 优化一：发布到线上集群添加交互式确认
强调一句话：如果是生产环境肯定不能开发人员push完毕后就直接部署到生产k8s集群中，只有develop分支才会push完自动完成整套流程发布到测试号环境，所以真正在应用的时候，应该区分对待master分支与develop分支

在Jenkinsfile文件中添加交互式代码（发布线上环境时确认是否发布、回滚功能）

##### 1.1 确认是否发布功能
```python
     // 添加交互代码，确认是否要部署到生产环境
                 def userInput = input(
                    id: 'userInput',
                    message: '是否确认部署到线上环境？',
                    parameters: [
                        [
                            $class: 'ChoiceParameterDefinition',
                            choices: "Y\nN",
                            name: '是否确认部署到线上环境?'
                        ]
                    ]
                  )
                  if (userInput == "Y") {
                    // 部署到线上环境 
                    sh "kubectl set image deployment/test test=${image}"
                  }else {
                    // 任务结束
                    echo "取消本次任务"
                  }
```

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1760859662143-d1df5662-2dbb-44bb-bb32-f175da88eb0c.png)

##### 1.2 回滚功能
```python
// 加入回滚功能，注意变量名不能与上面的冲突
                  def userInput2 = input(
                    id: 'userInput',
                    message: '是否需要快速回滚？',
                    parameters: [
                        [
                            $class: 'ChoiceParameterDefinition',
                            choices: "Y\nN",
                            name: '回滚?'
                        ]
                    ]
                  )
                  if (userInput2 == "Y") {
                    sh "kubectl rollout undo deployment/test"
                  } 

```

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1760859492121-a8a5a882-ef87-4350-9b01-8b4fc88ac517.png)

回滚前

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1760859561112-ea2e04d7-6a78-49b5-87a3-558636089d38.png)

回滚后

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1760859588497-728fa63a-49f6-4b76-96cf-85d697041041.png)



#### 优化二：为master分支设置保护规则（合并需全阶段流水线构建成功）
master分支对应线上环境，develop分支对应测试环境，需要在测试环境整套流水线发布运行无异常才能将develop分支代码合并入master分支，并将项目发布到线上环境。

清理git仓库环境，重新拉取

```python
 git push origin --delete develop
```

gitlab中配置(setting)只有流水线执行成功，才能合并

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756617662499-5d727160-fe99-42a2-8d0f-6d117c818856.png)

给流水线在Jenkinsfile中配置给gitlab的执行结果返回，这边采用的是调用gitlab接口的方式，大家可以思考一下别的模式可以怎么做

接口中需要有gitlab token、仓库id以及commit id

获取gitlab token，生成的token需要记录下来，刷新就看不到了

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756618317157-96cffa02-9dae-4976-a52e-98e34407dd21.png)

获取仓库 id

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756617550486-d35d4406-035b-4ab1-bd2d-7ca109be0d2d.png)



获取commit id，接口中需要传哈希值

```python
 def imageTag = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
```

完整接口

```python
curl --request POST --header 'PRIVATE-TOKEN: 59HQaqVRGXpcWRybxNGa' 'http://192.168.198.32:1180/api/v4/projects/3/statuses/${imageTag}?state=success'  成功 
curl --request POST --header 'PRIVATE-TOKEN: 59HQaqVRGXpcWRybxNGa' 'http://192.168.198.32:1180/api/v4/projects/3/statuses/${imageTag}?state=failed'  失败
```

触发合并（develop合入master）

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756618808276-c32e91c3-fe22-4b86-9b24-791c72bcb1f5.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754830746235-bdb6de0d-0def-4905-9d2b-93a57b9eda57.png?x-oss-process=image%2Fformat%2Cwebp)

流水线执行失败时

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756619089415-ee7b346e-5af1-4224-afff-a5cc8101ef7d.png)

流水线执行成功时

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756619106204-7c1da183-fa67-4654-a129-6d58c37ec85a.png)



整体Jenkinsfile

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
 
    try{
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
              withCredentials([file(credentialsId: 'kubeconfig-xianshang', variable: 'KUBECONFIG')]) {
                 echo "查看生产 K8S 集群 Pod 列表"
                 sh 'echo "${KUBECONFIG}"'
                 sh 'mkdir -p ~/.kube && /bin/cp "${KUBECONFIG}" ~/.kube/config'
                 sh "kubectl get pods"
                  
                 // 添加交互代码，确认是否要部署到线上环境
                 def userInput = input(
                    id: 'userInput',
                    message: '是否确认部署到线上环境？',
                    parameters: [
                        [
                            $class: 'ChoiceParameterDefinition',
                            choices: "Y\nN",
                            name: '是否确认部署到线上环境?'
                        ]
                    ]
                  )
                  if (userInput == "Y") {
                    // 部署到线上环境 
                    sh "kubectl set image deployment/test test=${image}"
                  }else {
                    // 任务结束
                    echo "取消本次任务"
                  } 

                  // 加入回滚功能，注意变量名不能与上面的冲突
                  def userInput2 = input(
                    id: 'userInput',
                    message: '是否需要快速回滚？',
                    parameters: [
                        [
                            $class: 'ChoiceParameterDefinition',
                            choices: "Y\nN",
                            name: '回滚?'
                        ]
                    ]
                  )
                  if (userInput2 == "Y") {
                    sh "kubectl rollout undo deployment/test"
                  } 
                  
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
    sh "curl --request POST --header 'PRIVATE-TOKEN: xcLGedyxLvPQLRzKTiBr' 'http://192.168.198.142:1180/api/v4/projects/1/statuses/${imageTag}?state=success'"
   } catch (Exception e) {
     sh "curl --request POST --header 'PRIVATE-TOKEN: xcLGedyxLvPQLRzKTiBr' 'http://192.168.198.142:1180/api/v4/projects/1/statuses/${imageTag}?state=failed'"
      error "Build failed"
   }
   }
}

```



#### 补充扩展
##### 单元测试
单元测试是一种验证代码正确性的重要方法，通常使用内置的 unittest 模块或第三方框架 pytest 来编写和运行测试用例。

通常分为4个部分

1.测试发现：从多个文件里面去找到我们的测试用例

2.测试执行：按照一定的顺序和规则去执行，并生成结果

3.测试判断：通过断言判断预期结果和实际结果的差异

4.测试报告：统计测试进度、耗时、通过率、生成测试报告（coverage工具）

例如，我们在编写一个简单的加法函数时：

```python
def add(x, y):
    return x + y
```

<font style="color:rgb(25, 27, 31);">我们可以通过编写一个简单的单元测试，来保证这个函数的功能：</font>

```python
import unittest

class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(1, 2), 3)
```



##### SonarQube扫描
SonarQube 是一个开源的代码质量管理平台，可以检测代码中的漏洞、重复代码、代码复杂度等问题

主要步骤

<font style="color:rgb(79, 79, 79);">1.安装 SonarQube</font>

<font style="color:rgb(79, 79, 79);">2.配置 Jenkins 与 SonarQube的互访</font>

<font style="color:rgb(79, 79, 79);">3.Jenkins 流水线集成 SonarQube（安装插件、编写Jenkinsfile）</font>

##### <font style="color:rgba(0, 0, 0, 0.75);">  
</font><font style="color:rgba(0, 0, 0, 0.75);">冒烟测试</font>
<font style="color:rgb(25, 27, 31);">在软件发布前快速验证系统的关键功能能否正常运作。</font>



##### 也可在同一集群中部署线上和测试环境(不是很建议)，通过名称空间来区分
如测试分支流水线（dev分支），自动部署到k8测试环境（namespace：dev）; 线上分支流水线（master分支），自动部署到k8s线上环境（namespace：prod）

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





### 第二部分：完成python爬虫项目的构建
##### 2.1 按照之前的思路，分为如下步骤
1、创建python 爬虫的gitlab仓库（之前已创建）

2、harbor创建一个存放python 爬虫镜像的仓库

3、在jenkin新建一条构建python爬虫项目的流水线，并打通gitlab

4、修改Jenkinsfile文件



##### 2.2 企业级项目目录结构
```python
/flask-crawler
├── app/                  # 核心应用代码
│   ├── __init__.py       # 应用工厂函数
│   ├── routes.py         # 主路由入口
│   ├── crawlers/         # 爬虫模块
│   │   ├── __init__.py
│   │   ├── douban.py     # 豆瓣爬虫实现
│   │   ├── weibo.py      # 微博爬虫（预留扩展）
│   │   └── base.py       # 爬虫抽象基类
│   ├── models/           # 数据模型
│   │   ├── __init__.py
│   │   └── result.py     # 爬虫结果模型
│   ├── services/         # 业务逻辑层（预留）
│   ├── utils/            # 工具函数
│   │   ├── logger.py     # 日志配置
│   │   └── validator.py  # 参数校验
│   ├── config.py         # 配置管理
│   └── extensions.py     # 扩展初始化
├── tests/                # 测试用例
│   ├── unit/             # 单元测试
│   └── functional/       # 功能测试
├── migrations/           # 数据库迁移脚本（自动生成）
├── requirements.txt      # 依赖清单
├── Dockerfile            # 容器构建文件
├── docker-compose.yml    # 本地开发环境
├── .dockerignore         # 容器排除文件
├── deploy/               # 部署配置
│   └── k8s/
│       ├── mysql/        # 数据库部署文件
│       └── app/          # 应用部署文件
└── scripts/              # 运维脚本
    ├── init_db.py        # 数据库初始化
    └── healthcheck.sh    # 健康检查
```





##### 2.3 Jenkinsfile（dockerfile展开版）
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

##### 2.4 优化Jenkinsfile
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

##### 2.5 构建成功
![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756615495860-b536ea25-a9ec-44b2-b2fa-68e4539ff71c.png)



### 第三部分：项目简历描述模板
项目名称：基于K8S构建cicd全自动流水线

项目描述：基于k8s部署gitlab+jenkins+harbor的全自动流水线，配置gitlab webhook和jenkins触发器，由开发机提交代码至gitlab时可一键触发jenkins全流程流水线构建(代码单元测试->代码编译打包->构建docker镜像并推送harbor镜像仓库->测试环境或线上环境自动拉取项目镜像并运行)

项目特点：jenkins采用了动态主从架构(master、slave pod)的部署方式，master为控制节点jenkins，构建不同项目时动态创建不同的jenkins slave pod，不用不创、用完即删，即有高可用性又可节省资源；流水线构建代码拆分出jenkins，以Jenkinsfile的形式放入项目中，缓解jenkins的压力；构建时通过gitlab分支区分不同构建环境(线上或测试环境)，构建时具备流水线回滚和发布前的确认功能，以及develop分支合并master分支时会自动校验测试环境全流水线是否执行成功



### 第四部分：课后作业：
1、优化go项目流水线的发布流程

2、完成python爬虫项目的构建

3、扩展部分：单元测试、<font style="color:rgb(51,51,51);">SonarQube 扫描、冒烟测试</font>





