# 云原生实战第四课：打通jenkin和gitlab（基础篇）
## 课程目标：
1、jenkins的一主多从模式及动态创建slave pod

2、构建自动化pipeline打通gitlab到jenkins



## 背景：
1、为什么要有jenkins主从模式：

因为日常构建Jenkins 任务中，会经常出现下面的情况:

+ 自动化测试需要消耗大量的CPU 和内存资源，如果服务器上还有其他的服务，可能会造成卡顿或者宕机;
+ Jenkins 平台项目众多，如果同一时间构建大量的任务，会出现多个任务抢占资源的情况。Jenkins提供了主从模式 (Master-Slave)解决这个问题。我们可以为Jenkins 配置多台slave 从机，当slave 从机和 Jenkins服务建立连接之后，由Jenkins 发指令给指定的slave 从机运行任务，消耗的资源由 slave 从机去承担。

2、为什么要构建自动化pipeline打通gitlab到jenkins

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



## jenkins主从模式
### 介绍
英文简称为 Master-Slave，基于分而治之、解耦合的核心思想，将一庞大的工作拆分，master主要负责基本管理、提供操作入口，例如流水线的创建与修改等，至于流水线的具体执行则交给slave去做。

### 传统jenkins一主多从模式的缺点
传统的jenkins一主多从架构是有缺点的

1、主Master 发生单点故障时，整个流程都不可用了

2、每个Slave 的配置环境不一样，来完成不同语言的编译打包等操作，但是这些差异化的配置导致管理起来非常不方便，维护起来也是比较费劲，

3、资源有浪费，每台Slave可能是物理机或者虚拟机，当 Slave 处于空闲状态时，也不会完全释放掉资源。或者有的Slave 要运行的job 出现排队等待，而有的Slave 处于空闲状态，



### 基于jenkins+k8s动态创建slave pod
针对传统jenkins一主多从的缺陷，我们将jenkins-master跑在k8s里提供故障恢复能力，并且配置动态创建jenkins-slave pod来解决上述2、3问题

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1753801806133-a065178a-f562-466e-8798-149740548953.png)

#### 操作步骤
步骤1：安装k8s 插件（用来动态创建slave pod）

我们需要安装 kubernetes 插件，点击 Manage Jenkins ->Manage Plugins ->Available ->Kubernetes 勾选安装即可。

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756052864301-1871527a-fb14-4776-8799-9cd7a22e6911.png)

步骤2：制作用于jenkins链接k8s的凭据

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
# openssl pkcs12 -export -out cert.pfx -inkey client.key -in client.crt -certfile ca.crt
Enter Export Password: 在此输入密码
Verifying - Enter Export Password: 在此输入密码
```

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756053240467-8d9495af-474a-461e-ac4e-d9cadd55cc59.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756053259913-91c9c8d1-066d-48a0-919f-f3d574f5aa48.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756053281718-b68cf10a-f83d-4499-8008-695f8dd2e484.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756053625874-20e6b8ce-94d9-4d39-a248-15682ebefc42.png)

步骤3：配置jenkins链接k8s集群

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756053917646-36895440-323c-4441-89f4-44e555742b41.png)

配置正确的话点连接测试，会显示链接成功

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756054244152-c6745011-1960-403f-892f-5359dcb484a0.png)填写jenkins的地址，此处可以填写svc地址，因为工具都部署k8s集群中

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756054408824-510e3c01-e7e8-4016-8a12-a9e8a85cdd19.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756054437715-b9f4343b-a034-4c60-bb02-8db8596f71c6.png)

步骤4：手动创建一个pod template

配置PodTemplate，本质就是配置JenkinsSlave运行的Pod模板，为了能够让大家快速看到jenkinslave以一个

pod的方式动态启动与销毁的效果，此处我们就先手动创建一个PodTemplate，你需要事先知道的时候，这个Pod

Template在后面我们是可以通过流水线代码自定义的，不同的流水线可以定义自己单独的PodTemplate，完全不

需要你在jenkins的web页面里手动创建一个固定死了的PodTemplate，我们此处手动创建只是会提前让你体验一

下动态床podslave的效果而已，后期这个手动创建的固定死了的podtemplate都是可以删掉的。

手动创建一个PodTemplate如下图操作，这里尤其注意Labels/标签列表，它非常重要，后面执行Job会通过该值

选中，然后我们这里先cnych/jenkins:jnlp6这个镜像，这个镜像是在官方的jnlp镜像基础上定制的，加入

了docker、kubectl等一些实用的工具

再次强调：此处我们添加一个podTemplate只是为了用于案例演示（它的配置包括镜像啥的对我们来说都没啥

用），后期我们会删掉该podTemplate，然后用pipeline脚本定制podTemplate、自己选择镜像，所以本小节手

动创建一个PodTemplate这一小节的所有步骤都只是为了演示，对后续的实际应用均没啥用。

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

另外，我们在步骤5，启动SlavePod执行测试命令时，有一条kubectl get pods查看pod信息，需要k8s权限才

行，所以我们需要创建一个ServiceAccount

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

步骤5：创建slave pod

jenkins首页->新建任务->输入一个任务名称、选择Freestyleproject类型的任务

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756058685999-8b670ee4-9526-427a-ac19-82e40de630e1.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756058833697-b61f58bd-525a-4c54-aed2-b13d9a074244.png)

然后往下拉，在Build区域选择Execute shell

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756059185262-4acd7b26-44bc-4e9a-9376-5956fa2865a5.png)

填入测试命令，点击保存

```plain
echo "测试 Kubernetes 动态生成 jenkins slave"
echo "==============docker in docker==========="
docker info
 
echo "=============kubectl============="
kubectl get pods
 
sleep 120
```

然后点击构建，并查看控制台输出

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756059554396-08410957-e9de-4b5c-82a5-9399b170e1f2.png)

实际会出现几个问题：

1、显示slave pod中jdk版本和jenkin默认的不符合![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756059793588-e92ec884-3909-49b6-8161-a47de5895973.png)

2、pod template中指定的镜像缺乏命令

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756060007253-cfa68f77-b27c-4cdf-860d-d86e6d2d9741.png)

解决思路：

第一个问题：指定jenkins中的jdk版本或更换pod template中的镜像为jdk11版本的jenkins/inbound-agent:jdk11

第二个问题：测试实验可更换shell中执行的命令

## 打通gitlab到jenkins
### jenkins的Pipeline有几个核心概念
Node：节点，一个Node 就是一个Jenkins 节点，Master 或者Agent，是执行 Step 的具体运行环境，比如我们之前动态运行的Jenkins Slave 就是一个Node 节点

Stage：阶段，一个Pipeline 可以定义多个Stage，每个Stage 代表一组操作，比如: Build、Test、Deploy, Stage 是一个逻辑分组的概念，可以跨多个Node

stages有如下特点:

所有stages 会按照顺序运行，即当一个stage 完成后，下一个stage 才会开始，只有当所有 stages 成功完成后，该构建任务(Pipeline)才算成功，如果任何一个stage 失败，那么后面的 stages 不会执行，该构建任务(Pipeline)失败

Step: 步骤，Step是最基本的操作单元，可以是打印一句话，也可以是构建一个Docker镜像，由各类Jenkins 插件提供，比如命令:sh 'make'，就相当于我们平时 shell终端中执行 make 命令一样。



### 创建jenkins中的pipeline的两种语法
Pipeline 脚本是由 Groovy语言实现的，但是我们泠必要单独去学习Groovy，用到啥查

Pipeline 支持两种语法：Declarative(声明式)和Scripted (脚本式)语法

例：

声明式：

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

脚本式：

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



### Pipeline 也有两种创建方法
#### 1、牛刀小试：script方式
主页-》新建任务/job-》输入一个任务名称，如test1-》点击流水线-》点击确定

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



#### 2、创建一条完整的由gitlab到jenkins的go项目的流水线：scm方式
通过创建一个Jenkinsfile脚本文件放入项目源码库中,然后jenkins配置SCM，点击构建后拉取源代码，jenkins会从源代码/项目根目录下载入Jenkinsfile文件来执行规定的构建(推荐该方式)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754227250982-57d4b157-ae35-4182-b4a5-97242d1634ab.png)

上面一步我们了解了如何创建pipeline，如何构建等基本流程，本节我们就创建一个SCM的流水线，然后完成构建后推送到k8s环境里。



我们的大致思路是。以一个go程序为例

一:在gitab里创建一个项目，该项目用来管理go程序，创建完毕后记录该项目的http或ssh链接信息

二:在jenkins里创建一个go的流水线

构建触发器，定义一个随机字符串作为token值，并选择Pipeline script from SCM，在SCM配置好代码仓库的链接信息

注意:不需要填写任何pipeline的代码

三:在gitlab里配置webhook

在gitlab里配置好webhook执行jenkins的地址，地址里包含在jenkins里生成的token值

四:编写一个名为Jenkinsfile的文件(强调首字母是一个大写的字母，看清楚了)，把pipeline的代码写到里面，然后扔给开发，开发人员会将该文件放到它的项目根目录下

五:go开发人员通过自己的开发机上传go项目代码(该项目根目录下包含一个名为jenkinsfile的文件)到

gitlab中的仓库redhat埋里，然后会按照jenkinsfile的规定触发一整套流程

所以看明白没有，如果是之前的python程序，套路也是一样，上面的一、二、三、四、五步走一遍，再创建一套针对python的就可以了



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



构建触发器

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754920956150-26f913d9-6807-4f04-aef8-89abe26aca05.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754921194654-e89e76d7-628a-408f-bead-3e0faee0bb0a.png)



配置用于构建的分支

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754921270343-d4541d0c-4e26-476e-a631-a38f80c87d97.png)



在gitlab中配置webhook

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754921548517-8f4655dc-aec1-4f32-a511-827e942bda19.png)

点击Add webhook，在屏幕上面会出现一行粉字:Url is blocked: Requests to the local network are notallowed则需要进入 GitLab首页，点击下图所示Admin Area->Settings ->NetWork->勾选 Outbound requests，然后->点击save changes

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754921740005-bf46a6f8-73fc-457e-8f84-783b6042c8c2.png)

点击save changes之后，回到项目的webhooks界面点击测试

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754922422956-4c6e7208-8cb4-4182-9515-278b7a9f6f71.png)

点击Push events后会报一个403错误，需要做三件事

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

安装完毕后重启，在url地址后输入restart，即:[http://192.168.198.32:709/](http://192.168.198.32:709/)restart

然后点击系统管理-》系统配置-》找到gitlab，去掉勾选:Enable authentication for '/project' end-point

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754923902409-bb5617a0-4d60-4144-902d-2de9ff470d1a.png)



然后再次点击test里的Push events，显示如下内容，代表手动触发push 事件成功

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754924065301-6b6d0f7e-e062-4be6-b801-854ce1f1e8ff.png)



编写Jenkinsfile

脚本式Jenkinsfile

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

如果测试环境和线上环境是两套集群，可以分开添加

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754926361311-bbdc2c16-5140-41c9-80cb-02f0808448ef.png)



![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754926671523-ad3555a9-5142-4a5a-9268-163d531a9a5b.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754926685492-08dafd05-777f-4e6f-a63e-cc2738711ecb.png)

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754926698724-04ba32d3-52ab-4cbb-a0a9-5ca3005b74f4.png)

```python
# 然后在 Jenkinsfile 的 kubectl 容器中读取上面添加的 Secret file 文件，拷贝到 ~/.kube/config 即可：
# 例如
stage('运行 Kubectl') {
  container('kubectl') {
    withCredentials([file(credentialsId: 'kubeconfig_ceshi', variable: 'KUBECONFIG')]) {
      echo "查看 K8S 集群 Pod 列表"
      sh "mkdir -p ~/.kube && cp ${KUBECONFIG} ~/.kube/config"
      sh "kubectl get pods"
    }
  }
}
```



在jenkins里创建一个登录harbor仓库的凭证

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754927202966-25b9d29f-477c-4a74-9dbd-e773058a6335.png)

在harbor创建一个存放go镜像的仓库

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1754927624822-97ce3342-f69e-4beb-b4d9-84fc9951da4f.png)



因为我们需要在k8s拉取harbor的私有仓库，需要用到账号密码，所以需要创建一个secret

```python
kubectl create secret docker-registry registry-secret --namespace=default \
--docker-server=192.168.198.32:30002 --docker-username=admin  \
--docker-password=Harbor12345
```



创建一个deployment

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
        image: 192.168.198.32:30002/redhat/initcontainer:v1.0
      imagePullSecrets:
      - name: registry-secret

```



往gitlab master和devlop分支提交一段go代码

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
    def registryUrl = "192.168.198.32:30002"
    def imageEndpoint = "redhat/gotest"
 
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



点击push之后，自动触发pipeline

![](https://cdn.nlark.com/yuque/0/2025/png/27742364/1756310779660-2b60eb5e-c7b4-4fca-8a0a-70a224a68813.png)



课后作业：

1、完成go项目的整个构建

2、思考前面的python爬虫项目如何进行构建

3、流水线是否有不完善的地方





