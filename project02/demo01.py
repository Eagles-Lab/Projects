# -*- coding: utf-8 -*-
# 引入依赖包
# 最低SDK版本要求：facebody20191230的SDK版本需大于等于4.0.8
# 可以在此仓库地址中引用最新版本SDK：https://pypi.org/project/alibabacloud-facebody20191230/
# pip install alibabacloud_facebody20191230

import os
import io
from urllib.request import urlopen
from alibabacloud_facebody20191230.client import Client
from alibabacloud_facebody20191230.models import CompareFaceAdvanceRequest
from alibabacloud_tea_openapi.models import Config
from alibabacloud_tea_util.models import RuntimeOptions

config = Config(
    # 创建AccessKey ID和AccessKey Secret，请参考https://help.aliyun.com/document_detail/175144.html。
    # 如果您用的是RAM用户的AccessKey，还需要为RAM用户授予权限AliyunVIAPIFullAccess，请参考https://help.aliyun.com/document_detail/145025.html。
    # 从环境变量读取配置的AccessKey ID和AccessKey Secret。运行代码示例前必须先配置环境变量。
    access_key_id=os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID'),
    access_key_secret=os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET'),
    # 访问的域名
    endpoint='facebody.cn-shanghai.aliyuncs.com',
    # 访问的域名对应的region
    region_id='cn-shanghai'
)
runtime_option = RuntimeOptions()
compare_face_request = CompareFaceAdvanceRequest()

#场景一：文件在本地
streamA = open(r'./1.png', 'rb')
compare_face_request.image_urlaobject = streamA

#场景二，使用任意可访问的url
# urlB = 'http://viapi-test.oss-cn-shanghai.aliyuncs.com/viapi-3.0domepic/facebody/CompareFace/CompareFace-left1.png'
# imgB = urlopen(urlB).read()
# compare_face_request.image_urlbobject = io.BytesIO(imgB)
streamB = open(r'./2.png', 'rb')
compare_face_request.image_urlbobject = streamB

try:
  # 初始化Client
  client = Client(config)
  response = client.compare_face_advance(compare_face_request, runtime_option)
  # 获取整体结果
  print(response.body)
except Exception as error:
  # 获取整体报错信息
  print(error)
  # 获取单个字段
  print(error.code)
  # tips: 可通过error.__dict__查看属性名称

# 关闭流
streamA.close()
streamB.close()