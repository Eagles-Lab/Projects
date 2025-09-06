# 云原生实战课程 - 第二课：Flask开发与K8s集成

---

## 课程目标
1. 掌握Flask基础开发能力
2. 实现带爬虫功能的REST API服务
4. 建立完整的云原生项目框架

**背景：**

新部门：已经创建好了 Jenkins+gitlab 平台以及交互，
SRE or 运维同学 在企业内部 --> 一般的开发都有那些?

基础架构部门： 学很多知识点 --> 对已有框架进行二次开发 k8s 等微服务 基本上都是用Go 去写的 （比较少） 因为有专门的研发去做这方面的开发
针对通用的一套项目
开发方面：（所有企业里都要用的） --->  最基本的 CRUD **调接口 传数据 存数据和运维分析**（业务运维 做的开发） 运维60-70 40-39 用来开发
django 做平台开发会好一些

flask 做一些接口 开发之类会快捷一些



sre 不是做主要的软件开发，大部分会开发什么东西？
在企业内部 会做一些对运维提效的工具 （类似于 自动化流程，以及数据分析工具）

## 第一部分：Flask基础教学（30分钟）

---

### 1.1 Flask核心概念（10分钟）

#### 核心组件三要素
```python
from flask import Flask, request, jsonify

# 1. 应用实例
app = Flask(__name__)  # __name__确定应用根目录

# 2. 路由定义
@app.route('/')
def index():
    # 3. 视图函数
    return "Welcome to devops Course!"

# 调试模式运行（生产环境需关闭）
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

### 案例1：动态路由

```python
@app.route('/user/<username>')
def show_user(username):
    return f'Hello {username}!'

@app.route('/post/<int:post_id>')
def show_post(post_id):
    return f'Post ID: {post_id}'
```

------

## 1.2 RESTful API设计（10分钟）

### 案例2：学生信息API

```python
students = [
    {'id': 1, 'name': 'water'},
    {'id': 2, 'name': 'wang'}
]

@app.route('/api/students', methods=['GET'])
def get_students():
    return jsonify({'students': students})

@app.route('/api/students', methods=['POST'])
def add_student():
    new_student = request.get_json()
    students.append(new_student)
    return jsonify(new_student), 201
```

1. **发送本地请求**

```bash
# 测试POST请求
curl -X POST http://localhost:5000/api/students   -H "Content-Type: application/json"   -d '{"id": 3, "name": "zhang"}'

curl http://localhost:5000/time/Asia/Shanghai

# 测试POST请求
curl -X POST -H "Content-Type: application/json" \
  -d '{"username":"test","password":"1234567"}' \
  http://localhost:5000/login
```

2. **调试技巧：**
   - 使用 `app.logger.debug()` 记录日志
   - 浏览器访问 `/time` 查看响应头信息
   - Postman测试复杂请求

### 现场练习1（5分钟）

```python
# 任务：创建时间查询接口
# 要求：
# 1. 访问 /time 返回当前时间（格式："2024-03-20 14:30:00"）
# 2. 访问 /time/<timezone> 返回带时区的时间（如 /time/utc）
# 提示：使用 datetime 模块

# 参考答案 ▼
from datetime import datetime
import pytz

@app.route('/time')
def current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@app.route('/time/<timezone>')
def timezone_time(timezone):
    try:
        tz = pytz.timezone(timezone)
        return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")
    except pytz.UnknownTimeZoneError:
        return "Invalid timezone", 400
```

------

## 1.3 请求处理与响应（10分钟）

### 请求处理三要素

```python
from  flask import Flask, jsonify, request

app = Flask(__name__)


@app.route('/submit', methods=['POST'])
def handle_submit():
    # 1. 获取参数
    form_data = request.form  # 表单数据
    json_data = request.json  # JSON数据
    args_data = request.args  # URL参数

    print(f"form_data为{form_data},json_data为{json_data},args_data为{args_data}")
    # 2. 业务处理
    # ... 处理逻辑 ...

    # 3. 构建响应
    return jsonify({
        'form': form_data,
        'json': json_data,
        'args': args_data
    }), 200

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
```

### 错误处理示例

```python
@app.errorhandler(404)
def page_not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Server internal error'}), 500
```

1. **表单数据 (`form_data`)**
   - **Content-Type**: `application/x-www-form-urlencoded` 或 `multipart/form-data`
   - **用途**: 传统HTML表单提交的数据（如`<form>`标签）
   - **获取方式**: `request.form` 会返回一个不可变字典（ImmutableMultiDict）
2. **JSON数据 (`json_data`)**
   - **Content-Type**: `application/json`
   - **用途**: 前端通过AJAX或API发送的JSON格式数据
   - **获取方式**: `request.json` 会自动解析请求体中的JSON数据
3. **URL参数 (`args_data`)**
   - **位置**: 附加在URL中的键值对，如 `http://url?name=foo&age=20`
   - **用途**: 常用于GET请求过滤或分页参数，但POST请求也可以携带URL参数
   - **获取方式**: `request.args` 会返回一个不可变字典

```bash
#验证
curl -X POST \
  "http://127.0.0.1:5000/submit?param1=url1&param2=url2" \
  -H "Content-Type: application/dict" \
  -d "field1=form1" \
  -d "field2=form2"
  
  curl -X POST \
  "http://127.0.0.1:5000/submit?param1=url1" \
  -H "Content-Type: application/json" \
  -d '{"key1": "json1", "key2": "json2"}'

```

### 现场练习2（5分钟）

```python
# 任务：创建用户登录接口
# 要求：
# 1. 接收POST请求（表单数据：username, password）
# 2. 验证用户名长度>3，密码长度>6
# 3. 返回 {"status": "success"} 或 {"error": "validation failed"}

# 参考答案 ▼
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    
    if len(username) > 3 and len(password) > 6:
        return jsonify({'status': 'success'})
    else:
        return jsonify({'error': 'validation failed'}), 400
```

## 

## 第二部分：项目框架搭建与工程化实践

调用其他方服务接口--> 进行数据处理 --》 提供给运维 做处理 （爬虫 类比调用其他服务方的接口 以及做数据处理）

---

### 企业级Flask应用场景
1. **微服务API网关**：处理请求路由和协议转换
2. **快速原型开发**：MVP产品验证阶段常用
3. **数据可视化平台**：结合Echarts等前端库
4. **IoT设备管理**：轻量级设备通信接口
5. <u>**自动化运维平台**：**与Ansible/Jenkins等集成**</u>

---

### 2.1 企业级项目结构详解

#### 项目目录结构（增强版）

```bash
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



### 核心文件说明
| 文件/目录         | 作用说明                                                     |
| ----------------- | ------------------------------------------------------------ |
| `app/__init__.py` | 应用工厂模式核心，初始化Flask实例，注册蓝图和扩展            |
| `extensions.py`   | 集中管理数据库、缓存等扩展实例，避免循环导入问题             |
| `utils/logger.py` | 企业级日志配置（JSON格式、分级存储），集成Sentry等监控平台   |
| `scripts/`        | 标准化运维脚本，保证开发/生产环境操作一致性                  |
| `deploy/k8s/`     | K8s资源定义文件，包含Deployment/Service/Ingress等完整部署单元 |

---

## 配置管理系统详解

企业内部一般分为四个环境

dev （本地环境） 本地测试环境

test  测试环境 （所有开发者 一同测试的环境）打包发布走流水线

pre  预发布（一般由我们的prod 环境克隆出来的）

prod 生产（线上运行版本）

### 1. 环境配置原理图解
```mermaid
graph TD
    A[环境变量FLASK_ENV] --> B{选择配置}
    B -->|development| C[开发配置]
    B -->|production| D[生产配置]
    C --> E[开启调试模式]
    C --> F[本地数据库]
    D --> G[关闭调试]
    D --> H[云数据库]
```

### 2. 配置关联流程
1. **入口文件**：当运行`flask run`时
2. **环境检测**：自动读取`FLASK_ENV`环境变量 .env文件里存储 --》 后续部署在k8s上 是可以通过configmap去集成配置的
3. **配置加载**：
   
   ```python
   # 类似选择游戏难度
   if 当前是新手村(development):
       使用新手装备(DevelopmentConfig)
   else:
       使用战斗装备(ProductionConfig)
   ```
4. **应用生效**：所有`app.config`访问都指向当前配置

### 3. 工厂模式通俗解释

#### 传统方式（对比理解）
```python
app = Flask(__name__)  # 直接创建app → 相当于买成品手机

@app.route('/')
def index(): ...
```

#### 工厂模式（推荐方式）模块化处理
```python
def create_app():  # 手机组装工厂
    app = Flask(__name__)  # 主板
    
    # 安装组件（可定制）
    app.config.install(DevelopmentConfig)  # 开发版芯片
    db.install(app)  # 内存条
    
    return app  # 组装完成的手机
```

优势：
- 方便更换零件（不同配置）
- 延迟组装（需要时才创建）
- 方便测试（可创建多个测试机）

### 4. 核心概念拆解 

#### 蓝图（Blueprint）类比 

面向对象的主要思想： 模块化处理，减少代码冗余 重复利用

- **传统方式**：所有路由写在单文件中 → 类似把卧室、厨房、卫生间都放在一个大房间
- **蓝图方式**：
  
  ```python
  # routes.py → 户型设计图
  bp = Blueprint('api', __name__)  # 设计一个房间
  
  @bp.route('/users')  # 在房间里放床
  def users(): ...
  
  # __init__.py → 按设计图盖房子
  app.register_blueprint(bp)  # 添加这个房间
  ```

#### 扩展初始化（Extensions）
- **什么是扩展**：给Flask添加额外功能的工具包（数据库、缓存等）

  #### 扩展集中管理

  ```python
  # app/extensions.py
  from flask_sqlalchemy import SQLAlchemy
  from flask_caching import Cache
  
  db = SQLAlchemy()
  cache = Cache(config={'CACHE_TYPE': 'RedisCache', 'CACHE_REDIS_URL': 'redis://redis:6379/0'})
  ```

  ---

  ### 

- **初始化过程**：
  ```python
  # 买来未组装的家具（扩展对象）
  db = SQLAlchemy()  # 买了个未拆封的衣柜
  
  # 在工厂里组装（初始化）
  def create_app():
      app = Flask(__name__)
      db.init_app(app)  # 把衣柜安装到房间里
  ```

### 5. 配置使用示例

#### 在代码中获取配置
```python
from flask import Blueprint, current_app
from .extensions import db

bp = Blueprint('api', __name__)

@bp.route('/users')
def users():
    return {'message': 'User endpoint works!'}

@bp.route('/config')
def show_config():
    """配置查看接口"""
    return {
        'environment': current_app.config['ENV'],  # 改用config访问
        'debug': current_app.config['DEBUG'],
        'database': current_app.config['SQLALCHEMY_DATABASE_URI'],
        'secret_key': current_app.config['SECRET_KEY'][:3] + '***'
    }

@bp.route('/db-check')
def db_check():
    """数据库连接检查"""
    try:
        db.engine.execute('SELECT 1')
        return {'db_status': 'connected'}
    except Exception as e:
        return {'db_status': str(e)}, 500
```

#### 环境切换实践
```bash
# 开发环境（使用.env文件）
echo "FLASK_ENV=development" > .env
flask run

# 生产环境（命令行指定）
FLASK_ENV=production 
flask run
```

---

#### 企业级配置实践

1. **敏感信息管理**：

   - 使用K8s Secrets或Vault管理凭证
   - 禁止在代码中硬编码敏感信息

2. **环境隔离**：

   ```bash
   # .env文件示例
   FLASK_ENV=development
   DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/dev_db
   RATE_LIMIT=100/小时
   ```

3. **动态配置**：

   ```python
   # 集成Consul等配置中心
   import consul
   consul_client = consul.Consul()
   index, config_data = consul_client.kv.get('app/config')
   ```

## 演示步骤

### 1. 配置系统体验
1. 在`.env`中添加：
   ```bash
   FLASK_ENV=development
   SECRET_KEY=mydevkey123
   DATABASE_URL=sqlite:///dev.db
   ```
2. 修改`config.py`：
   ```python
   # app/config.py
   import os
   from dotenv import load_dotenv
   
   load_dotenv()  # 加载.env文件
   
   
   class Config:
       # 基础配置
       SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')
       JSON_AS_ASCII = False  # 支持中文响应
       ENV = os.getenv('FLASK_ENV')
       # 数据库配置
       SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
       SQLALCHEMY_ENGINE_OPTIONS = {
           'pool_size': 10,
           'pool_recycle': 300,
           'pool_pre_ping': True
       }
   
   
   class DevelopmentConfig(Config):
       DEBUG = True
       TESTING = True
       SQLALCHEMY_ECHO = True  # 输出SQL日志
   
   
   class ProductionConfig(Config):
       DEBUG = False
       PROPAGATE_EXCEPTIONS = True  # 生产环境异常传递
   
   
   config = {
       'development': DevelopmentConfig,
       'production': ProductionConfig
   }
   
   ```
3. 在路由中访问配置：
   ```python
   from flask import Blueprint, current_app
   from .extensions import db
   
   bp = Blueprint('api', __name__)
   
   @bp.route('/users')
   def users():
       return {'message': 'User endpoint works!'}
   
   @bp.route('/config')
   def show_config():
       """配置查看接口"""
       return {
           'environment': current_app.config['ENV'],  # 改用config访问
           'debug': current_app.config['DEBUG'],
           'database': current_app.config['SQLALCHEMY_DATABASE_URI'],
           'secret_key': current_app.config['SECRET_KEY'][:3] + '***'
       }
   
   @bp.route('/db-check')
   def db_check():
       """数据库连接检查"""
       try:
           db.engine.execute('SELECT 1')
           return {'db_status': 'connected'}
       except Exception as e:
           return {'db_status': str(e)}, 500
   ```

__init__.py

```python
# app/__init__.py
from flask import Flask
from .config import config
from .extensions import db, cache
from .routes import bp


def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # 初始化扩展
    db.init_app(app)
    cache.init_app(app)

    # 注册蓝图

    app.register_blueprint(bp)

    # 初始化数据库
    with app.app_context():
        db.create_all()

    return app
```

wsgi.py

```python
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
```



### 2. 工厂模式动手实验

**步骤**：
1. 创建一个`create_app`函数
2. 尝试用不同配置创建两个app实例
3. 分别访问`/debug`接口观察输出

**示例代码**：
```python
dev_app = create_app('development')
prod_app = create_app('production')

with dev_app.app_context():
    print(dev_app.config['DEBUG'])  # 输出 True

with prod_app.app_context():
    print(prod_app.config['DEBUG'])  # 输出 False
```

### 3. 蓝图拆分练习
**任务**：将以下路由拆分到`auth.py`蓝图

```python
@app.route('/login')
def login(): ...

@app.route('/logout')
def logout(): ...
```

**参考答案**：

```python
# auth.py
from flask import Blueprint

bp = Blueprint('auth', __name__)

@bp.route('/login')
def login(): ...

# __init__.py
from .auth import bp as auth_bp
app.register_blueprint(auth_bp, url_prefix='/auth')
```

---

## 常见问题解答

### Q1：为什么要用工厂模式？
- 场景类比：奶茶店制作不同口味的奶茶
  - 传统模式：每杯奶茶单独从头制作 → 效率低
  - 工厂模式：准备好基础原料（create_app），按需添加不同配料（配置）

### Q2：环境变量在哪里设置？
- 开发环境：`.env`文件（不要提交到Git）
- 生产环境：
  ```bash
  # Linux/Mac
  export FLASK_ENV=production
  
  # Kubernetes
  kubectl create secret generic flask-env --from-env-file=.env
  ```

### Q3：如何检查当前生效配置？
```python
# 在路由中打印
print(app.config.items()) 

# 或启动时显示
if __name__ == '__main__':
    app = create_app()
    print("当前运行环境:", app.config['ENV'])
    app.run()
```



### 2.4 企业级最佳实践

1. **接口安全**：
   - 添加JWT身份验证
   - 请求参数签名验证
   - CORS跨域控制
2. **日志规范**：

---

### **1. 接口安全与监控装饰器**
```python
# app/decorators.py
import time
from functools import wraps
from flask import request, jsonify, g
import logging

logger = logging.getLogger('api')


def log_request(f):
    """请求日志记录装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        start_time = time.time()
        try:
            response = f(*args, **kwargs)
            duration = round((time.time() - start_time)*1000, 2)
            logger.info('Request processed', extra={
                'endpoint': request.endpoint,
                'method': request.method,
                'path': request.full_path,
                'duration_ms': duration,
                'user': getattr(g, 'user', None)
            })
            return response
        except Exception as e:
            logger.error('Request failed', exc_info=True)
            raise

    return decorated
```

---

### **2. 日志系统配置**
```python
# app/__init__.py

    # 统一配置所有环境的日志
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(  # 使用 JSON 格式化
        '%(asctime)s %(name)s %(levelname)s %(message)s %(endpoint)s %(method)s %(path)s %(duration_ms)s'
    )
    handler.setFormatter(formatter)

    # 同时配置 Flask 主日志和自定义日志
    for logger_name in ('api', 'werkzeug'):
        logger = logging.getLogger(logger_name)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG if app.debug else logging.INFO)
```

---

### **3. 路由集成示例**
```python
from flask import Blueprint
from .decorators import  log_request

bp = Blueprint('auth', __name__)


@bp.route('/login')
def login():
    return {'message': 'this is login'}


@bp.route('/logout')
def logout():
    return {'message': 'this is logout'}


@bp.route('/public-api')
@log_request
def public_api():
    """公共接口示例"""
    return {'status': 'public access allowed'}
```



| 功能               | 实现方式                       | 企业级价值                                 |
| ------------------ | ------------------------------ | ------------------------------------------ |
| **统一身份认证**   | 通过`@auth_required`装饰器     | 集中管理API访问权限，符合零信任安全模型    |
| **请求全链路追踪** | `@log_request`记录耗时和元数据 | 便于性能分析和异常排查                     |
| **分层日志管理**   | 根据环境配置不同日志级别       | 生产环境减少冗余日志，开发环境保留调试信息 |
| **非侵入式集成**   | 装饰器叠加使用                 | 不影响业务逻辑代码的简洁性                 |

---

### **生产环境日志示例**
```log
{"asctime": "2025-03-16 01:05:27,398", "name": "werkzeug", "levelname": "INFO", "message": "127.0.0.1 - - [16/Mar/2025 01:05:27] \"GET /auth/public-api HTTP/1.1\" 200 -", "endpoint": null, "method": null, "path": null, "duration_ms": null}
```

### 教学提示
1. **框架设计原则**：
   - 单一职责原则（每个目录/文件职责明确）
   - 开闭原则（通过继承BaseCrawler扩展新平台）
   - 依赖倒置原则（高层模块不依赖具体实现）

2. **常见问题解析**：
   - 循环导入问题：通过工厂模式和extensions.py解决
   - 配置覆盖问题：环境变量 > 配置文件 > 默认值
   - 多环境适配：通过FLASK_ENV切换不同配置

3. **企业案例演示**：
   - 展示知名公司（如Netflix）的微服务架构图
   - 对比单体应用与微服务项目结构差异

---

# 第三部分：爬虫服务开发与框架集成

---

## 教学目标
1. 理解工厂模式在爬虫服务中的应用
2. 掌握RESTful API开发规范
3. 实现安全可靠的爬虫服务
4. 掌握企业级异常处理方案

---

## 项目目录结构详解

```bash
/flask-crawler
├── app/
│   ├── __init__.py          # 应用工厂（相当于手机组装车间）
│   ├── routes.py           # 主路由（相当于手机触控屏）
│   ├── crawlers/           # 爬虫模块（相当于摄像头模组）
│   │   ├── __init__.py
│   │   ├── base.py         # 爬虫基类（通用摄像头设计图）
│   │   └── douban.py       # 豆瓣爬虫（专用摄像头实现）
│   ├── models/             # 数据模型（相当于存储芯片）
│   │   ├── __init__.py
│   │   └── result.py       # 爬虫结果模型
│   ├── services/           # 业务逻辑（相当于处理器）
│   │   └── crawler_service.py
│   ├── utils/              # 工具类（相当于螺丝刀等工具）
│   │   ├── decorators.py   # 装饰器
│   │   └── logger.py       # 日志工具
│   ├── config.py           # 配置（相当于手机设置菜单）
│   └── extensions.py       # 扩展（相当于外接配件接口）
├── tests/                  # 测试用例（质量检测部门）
│   ├── unit/               # 单元测试
│   │   └── test_crawlers.py
│   └── functional/         # 功能测试
│       └── test_api.py
├── requirements.txt        # 依赖清单（配件采购列表）
└── wsgi.py                 # 入口文件（电源开关）
```

---

## 核心文件调用关系图解

```mermaid
graph TD
    A[routes.py] -->|导入| B[crawler_service.py]
    B -->|使用| C[base.py]
    C -->|继承| D[douban.py]
    A -->|注册| E[__init__.py]
    E -->|初始化| F[extensions.py]
    F -->|连接| G[config.py]
    G -->|读取| H[.env]
```

## 

# 分步实现方案

作为sre 实习生：一般情况 分配任务 就是一些简单的调接口 （爬虫去代替了）

---

## 1. 豆瓣Top250爬虫实现

bs环境安装

> pip install bs4
>
> pip install lxml

### 爬虫基类 (`app/crawlers/base.py`)

```python
from .base import BaseCrawler
from time import sleep


class DoubanCrawler(BaseCrawler):
    def fetch_data(self, keyword=None):
        """获取豆瓣Top250电影"""
        movies = []

        for start in range(0, 250, 25):
            url = f"https://movie.douban.com/top250?start={start}"
            response = self.session.get(url)
            response.raise_for_status()

            movies.extend(self._parse_page(response.text))
            sleep(2)  # 保持礼貌爬取间隔

        return movies

    def _parse_page(self, html):
        """解析页面（简化版）"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')
        return [{
            'title': item.select_one('.title').text.strip(),
            'rating': item.select_one('.rating_num').text.strip(),
            'link': item.select_one('a')['href']
        } for item in soup.select('.item')]
```



### 豆瓣爬虫实现 文件位置：`app/crawlers/douban.py`

```python
from .base import BaseCrawler
from time import sleep


class DoubanCrawler(BaseCrawler):
    def fetch_data(self, keyword=None):
        """获取豆瓣Top250电影"""
        movies = []

        for start in range(0, 250, 25):
            url = f"https://movie.douban.com/top250?start={start}"
            response = self.session.get(url)
            response.raise_for_status()

            movies.extend(self._parse_page(response.text))
            sleep(2)  # 保持礼貌爬取间隔

        return movies

    def _parse_page(self, html):
        """解析页面（简化版）"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')
        return [{
            'title': item.select_one('.title').text.strip(),
            'rating': item.select_one('.rating_num').text.strip(),
            'link': item.select_one('a')['href']
        } for item in soup.select('.item')]
```

---

## 2. CSV存储服务实现

### 文件位置：`app/services/crawler_service.py`

```python
import csv
import os
from datetime import datetime
from ..extensions import db  # 统一从extensions导入
from ..models.result import CrawlResult
from pathlib import Path


def save_to_csv(data, filename=None):
    """保存到项目根目录的data文件夹"""
    # 项目根目录路径（根据实际结构调整）
    BASE_DIR = Path(__file__).parent.parent.parent  # 假设服务层在 app/services/

    # 构建绝对路径
    data_dir = BASE_DIR / 'data'
    data_dir.mkdir(exist_ok=True)

    if not filename:
        filename = data_dir / f"douban_top250_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['title', 'rating', 'link'])
        writer.writeheader()
        writer.writerows(data)

    # 返回相对路径便于展示
    return str(filename.relative_to(BASE_DIR))

def execute_crawl(platform: str):
    """执行爬取任务"""
    from ..crawlers.douban import DoubanCrawler  # 使用绝对路径导入

    try:
        crawler = DoubanCrawler()
        movies = crawler.fetch_data()

        # 保存到CSV
        csv_path = save_to_csv(movies)
        print(f"CSV文件已保存到：{csv_path}")  # 添加调试输出

        # 保存到数据库
        record = CrawlResult(
            platform=platform,
            data={'count': len(movies), 'path': csv_path}
        )
        db.session.add(record)
        db.session.commit()

        return record
    except Exception as e:
        db.session.rollback()
        raise e
```

---

## 3. 数据库模型定义

### 文件位置：`app/models/result.py`

```python
from ..extensions import db
from datetime import datetime

class CrawlResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50))
    data = db.Column(db.JSON)  # 存储路径和记录数
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'platform': self.platform,
            'file_path': self.data.get('path'),
            'count': self.data.get('count'),
            'created_at': self.created_at.isoformat()
        }
```

---

## 4. 路由接口实现

### 文件位置：`app/routes/crawl.py`

```python
from flask import Blueprint, jsonify
from .services.crawler_service import execute_crawl
from .utils.decorators import log_request

bp = Blueprint('crawl', __name__)


@bp.route('/douban-top250', methods=['POST'])
@log_request
def crawl_douban():
    try:
        record = execute_crawl(platform='douban')
        return jsonify(record.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

---

## 5. 使用测试

### 请求示例
```bash
$ curl -X POST http://localhost:5000/crawl/douban-top250

```

### 预期响应
```json
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   156  100   156    0     0      6      0  0:00:26  0:00:22  0:00:04    46{
  "count": 250,
  "created_at": "2025-03-15T18:31:09.752563",
  "file_path": "data\\douban_top250_20250316_0231.csv",
  "id": 2,
  "platform": "douban"
}

```

### 生成的文件示例
```csv
title,rating,link
肖申克的救赎,9.7,https://movie.douban.com/subject/1292052/
霸王别姬,9.6,https://movie.douban.com/subject/1291546/
...
```

---

## 教学说明

### 1. 代码结构关系
```mermaid
graph LR
    A[路由/crawl/douban-top250] --> B[服务层execute_crawl]
    B --> C[豆瓣爬虫fetch_data]
    C --> D[保存CSV]
    B --> E[保存数据库]
```

### 2. 运行前准备
```bash
# 安装新增依赖
pip install beautifulsoup4
```

### 3. 教学要点
1. 分页处理逻辑：通过?start参数控制页码
2. 礼貌爬虫：请求间隔设置
3. 数据持久化：CSV与数据库双存储
4. 异常处理：数据库事务回滚
5. 文件管理：自动创建data目录

---

## 模块调用流程示例

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant Route as 路由层
    participant Service as 服务层
    participant Crawler as 爬虫
    participant DB as 数据库

    Client->>Route: POST /crawl {platform: 'douban'}
    Route->>Service: 调用execute_crawl()
    Service->>Crawler: 创建豆瓣爬虫实例
    Crawler->>Crawler: 执行网页抓取
    Service->>DB: 保存结果
    DB-->>Service: 返回保存记录
    Service-->>Route: 返回结果
    Route-->>Client: 返回JSON响应
```

---

## 教学重点解析

### 1. 分层架构类比
- **路由层**：类似手机触摸屏，处理用户输入输出
- **服务层**：类似手机CPU，处理核心业务逻辑
- **数据层**：类似手机存储器，负责数据持久化
- **工具层**：类似手机工具包，提供通用功能

### 2. 工厂模式理解
```python
# 想象一个汽车工厂
class CarFactory:
    @classmethod
    def create_car(cls, type):
        if type == "suv":
            return SUV()
        elif type == "sedan":
            return Sedan()

# 就像这样创建爬虫：
crawler = BaseCrawler.create('douban')
```

### 3. 异常处理示例
```python
try:
    result = crawler.fetch_data(keyword)
except requests.exceptions.Timeout:
    logger.error("请求超时")
    return {"error": "请求超时，请重试"}, 504
except Exception as e:
    logger.exception("未知错误")
    return {"error": "服务器内部错误"}, 500
```

---

### 实现不同参数请求不同页面爬虫

在已有的基础上**支持多类型爬取的完整改造方案**

```python
#base.py
from abc import ABC, abstractmethod
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class BaseCrawler(ABC):
    """支持多站点的爬虫基类"""

    def __init__(self, crawl_type='movies'):
        self.crawl_type = crawl_type  # 新增类型参数
        self._init_session()

    def _init_session(self):
        """初始化网络会话"""
        self.session = requests.Session()

        retries = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504]
        )
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        })

    @classmethod
    def create(cls, platform: str, crawl_type: str):
        """增强的工厂方法"""
        from . import douban_movie, douban_book  # 动态导入

        _crawlers = {
            'douban_movie': douban_movie.DoubanMovieCrawler,
            'douban_book': douban_book.DoubanBookCrawler
        }
        return _crawlers[platform](crawl_type)

    @abstractmethod
    def get_base_url(self) -> str:
        """获取基础URL（由子类实现）"""
        pass

    def fetch_data(self):
        """通用爬取流程"""
        results = []
        # 豆瓣图书每页显示 25 条，共 10 页（250 条）
        for start in range(0, 250, 25):
            url = f"{self.get_base_url()}?start={start}"
            response = self.session.get(url)
            response.raise_for_status()  # 确保请求成功
            results.extend(self.parse(response.text))
        return results

    @abstractmethod
    def parse(self, html: str) -> list:
        """解析方法（由子类实现）"""
        pass
```

新建douban_movie&book

```python
from .base import BaseCrawler
from bs4 import BeautifulSoup
import time


class DoubanMovieCrawler(BaseCrawler):
    def get_base_url(self):
        return "https://movie.douban.com/top250"

    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        return [{
            'type': 'movie',
            'title': item.select_one('.title').text.strip(),
            'rating': float(item.select_one('.rating_num').text),
            'link': item.select_one('a')['href']
        } for item in soup.select('.item')]
    
from .base import BaseCrawler
from bs4 import BeautifulSoup
import time

#book.py
class DoubanBookCrawler(BaseCrawler):
    def get_base_url(self):
        return "https://book.douban.com/top250"

    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        # 调整选择器为豆瓣图书实际结构
        for item in soup.select('tr.item'):
            title_tag = item.select_one('div.pl2 a')
            rating_tag = item.select_one('span.rating_nums')
            link_tag = title_tag  # 标题和链接通常在同一标签

            # 允许 rating 为空（部分书籍可能无评分）
            if not (title_tag and link_tag):
                continue

            items.append({
                'type': 'book',  # 添加该字段
                'title': title_tag.text.strip().replace('\n', ''),
                'rating': float(rating_tag.text) if rating_tag else 0.0,
                'link': link_tag['href']
            })
        return items
```

调整service.py

```python
import csv
import os
from datetime import datetime
from ..extensions import db  # 统一从extensions导入
from ..models.result import CrawlResult
from pathlib import Path
from ..crawlers.base import BaseCrawler


def save_to_csv(data, filename=None):
    BASE_DIR = Path(__file__).parent.parent.parent
    data_dir = BASE_DIR / 'data'
    data_dir.mkdir(exist_ok=True)
    fieldnames = ['type', 'title', 'rating', 'link']  # 统一字段

    if not filename:
        filename = f"douban_top250_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

    # 将 filename 转换为 Path 对象，并与 data_dir 拼接
    file_path = data_dir / Path(filename)

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    return str(file_path.relative_to(BASE_DIR))  # 正确调用 Path 对象的方法


def execute_crawl(platform: str, crawl_type: str):
    """支持类型参数的执行方法"""
    try:
        crawler = BaseCrawler.create(platform, crawl_type)
        items = crawler.fetch_data()
        print(f"抓取到 {len(items)} 条数据")

        # 仅生成文件名（不包含路径）
        filename = f"{platform}_{crawl_type}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        csv_path = save_to_csv(items, filename)  # 传递纯文件名

        # 数据库记录
        record = CrawlResult(
            platform=platform,
            data={
                'type': crawl_type,
                'count': len(items),
                'path': csv_path
            }
        )
        db.session.add(record)
        db.session.commit()

        return record
    except Exception as e:
        db.session.rollback()
        raise e
```

**验证：**

```bash
$ curl -X POST http://localhost:5000/crawl/api/v1/crawl \
>   -H "Content-Type: application/json" \
>   -d '{"platform":"douban_movie","type":"movies"}'
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   211  100   168  100    43     65     16  0:00:02  0:00:02 --:--:--    82{
  "count": 250,
  "created_at": "2025-03-16T08:59:16.555203",
  "file_path": "data\\douban_movie_movies_20250316_1659.csv",
  "id": 6,
  "platform": "douban_movie"
}
```



## 学生动手实验

### 法律合规要点
1. 严格遵守目标网站 robots.txt 规则
2. 设置合理的请求间隔（建议≥3秒）
3. 禁止爬取个人隐私数据
4. 在HTTP头中添加联系方式：
```python
DEFAULT_HEADERS = {
    'User-Agent': 'CourseDemo/1.0 (contact: admin@course.com)'
}
```

1. **代码结构建议**
   ```python
   # 推荐分层结构
   app/
     ├── crawlers/    # 爬虫实现
     ├── tasks/       # 异步任务
     ├── schemas/     # 数据校验
     └── clients/     # 第三方API调用
   ```

2. **常见问题排查**
   - 403错误：检查请求头和IP限制
   - 超时问题：调整timeout参数或使用代理
   - 解析失败：定期更新CSS选择器
   - 封禁处理：实现自动切换代理IP池

---

## 课程总结

1. 完成从Flask开发到K8s部署的完整链路
2. 实现云原生应用的关键要素：
   - 微服务架构
   - 配置与密钥管理
   - 持久化存储
   - 服务发现
3. 为后续CI/CD流水线打下基础

---

## 课后作业

1. 需要大家把http://10.3.213.101:30088/gitlab-instance-5ba91dd4/new-flask 这个仓库拉下来基于main创建自己的分支
2. 基于当前的BaseCrawler 爬虫基类 集成 创建新的文件 去爬 weibo.py 信息 存储到本地csv
3. 在工厂方法（__init__）中注册新平台
4. 手动post测试 写的接口， 以及提交本地代码到仓库
备注：具体 git相关的学习资料 课下我整理发给你们 然后下节课开头讲一下







### 任务1：添加新平台爬虫

1. 在`crawlers`目录新建`weibo.py`
2. 继承`BaseCrawler`实现微博爬虫
3. 在工厂方法中注册新平台
4. 测试`POST /crawl`接口

### 任务2：添加缓存功能

```python
# 在services/crawler_service.py中添加
from app.extensions import cache

@cache.memoize(timeout=3600)
def execute_crawl(platform: str, keyword: str):
    # 原有逻辑...
```

### 基础练习

```python
# 任务1：实现GitHub爬虫
# 要求：
# 1. 继承BaseCrawler
# 2. 爬取GitHub搜索接口（https://api.github.com/search/repositories?q=）
# 3. 返回仓库名称和star数前5的结果

# 任务2：添加请求缓存
# 使用redis缓存相同参数的请求结果（缓存1小时）
```

