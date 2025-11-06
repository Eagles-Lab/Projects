# 新增工作节点：添加1台node

参考课件 `安装手册`

后续但凡需要重复性的工作？都需要要有自动化的意识 （效率大幅提升，标准化的操作可以溯源不会因为个人误操作而产生预期外的问题）
1. 单节点：LAMP 搭建
2. 单节点：docker 环境的部署
3. 多节点： nginx作为LB + keepalived + web服务
4. K8s集群的搭建：多节点部署

shell（单个shell文件尽量不要超过100行） + python（更复杂的逻辑， API接口的调用）+ ansible（规模化 1000+ 基本能够cover住）+ python/go （平台化）


注意点：
1. 脚本要是幂等性的？多次执行不会影响脚本正常逻辑
2. 网络初始化？比较少去配置固定IP；机房人员把IP配置好交付给业务，公有云创建虚拟机的时候基本定义好了IP

# 水平扩缩容

参考课件 `HPA控制器`：里面的实验一定要去做并且在我现有环境下观察指标和现象，根据策略的阈值扩缩容POD副本数量

# [扩展] 垂直扩缩容 
根据策略扩缩 pod cpu/mem 的request和limit

参考官网 https://v1-29.docs.kubernetes.io/zh-cn/docs/concepts/workloads/autoscaling/
https://github.com/kubernetes/autoscaler/tree/9f87b78df0f1d6e142234bb32e8acbd71295585a/vertical-pod-autoscaler


# [扩展] 高可用相关
1. k8s master 节点的高可用方案？（必须去了解的，如果能够实践一遍更佳）
2. 基于K8s的MySQL高可用方案
3. 基于K8s的Redis高可用方案



