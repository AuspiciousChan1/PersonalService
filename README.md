# PersonalService

一个基于 Django 的个人服务应用，提供访客记录功能的欢迎页面。

## 功能特性

- 🏠 **欢迎主页**: 精美的中文欢迎页面，带有渐变紫色背景
- 📊 **访客追踪**: 自动记录每次访问的信息到数据库
- 🔍 **后台管理**: Django Admin 界面查看和管理访客记录
- 🗄️ **PostgreSQL 数据库**: 使用 PostgreSQL 作为数据存储

## 技术栈

- **框架**: Django 6.0
- **数据库**: PostgreSQL
- **Python**: 3.8+

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/AuspiciousChan1/PersonalService.git
cd PersonalService
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install django psycopg2-binary
```

### 4. 配置数据库

确保 PostgreSQL 已安装并运行，然后创建数据库：

```bash
# 登录 PostgreSQL
psql -U postgres

# 创建数据库
CREATE DATABASE personalservice;

# 退出
\q
```

如需修改数据库配置，请编辑 `PersonalService/settings.py` 中的 `DATABASES` 设置：

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'personalservice',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 5. 运行数据库迁移

```bash
python manage.py migrate
```

### 6. 创建超级用户（可选）

```bash
python manage.py createsuperuser
```

### 7. 启动开发服务器

```bash
python manage.py runserver
```

访问 http://127.0.0.1:8000/ 查看欢迎页面。

访问 http://127.0.0.1:8000/admin/ 进入管理后台。

## 项目结构

```
PersonalService/
├── PersonalService/          # 项目配置目录
│   ├── settings.py          # 项目设置
│   ├── urls.py              # URL 路由配置
│   ├── wsgi.py              # WSGI 配置
│   └── asgi.py              # ASGI 配置
├── home/                    # 主页应用
│   ├── models.py            # 数据模型 (VisitorLog)
│   ├── views.py             # 视图函数
│   ├── admin.py             # Admin 配置
│   ├── templates/           # 模板文件
│   │   └── home/
│   │       └── index.html   # 欢迎页面模板
│   └── migrations/          # 数据库迁移文件
├── manage.py                # Django 管理脚本
└── README.md                # 项目说明文档
```

## 数据模型

### VisitorLog

记录访客信息的数据模型：

| 字段 | 类型 | 说明 |
|------|------|------|
| ip_address | GenericIPAddressField | 访客 IP 地址（支持 IPv4/IPv6） |
| user_agent | TextField | 浏览器用户代理字符串 |
| path | CharField | 访问的 URL 路径 |
| timestamp | DateTimeField | 访问时间（自动记录） |

## 功能说明

### 访客记录

每当有用户访问主页时，系统会自动记录以下信息：

- **IP 地址**: 支持通过 X-Forwarded-For 头获取真实 IP（适用于代理/负载均衡场景）
- **用户代理**: 记录浏览器和操作系统信息
- **访问路径**: 记录用户访问的具体路径
- **访问时间**: 自动记录访问的精确时间

### 后台管理

在 Django Admin 中可以：

- 查看所有访客记录
- 按时间过滤访客记录
- 搜索特定 IP 或用户代理
- 查看详细的访客信息

## 开发

### 运行测试

```bash
python manage.py test
```

### 创建新的应用

```bash
python manage.py startapp <app_name>
```

### 数据库迁移

```bash
# 创建迁移文件
python manage.py makemigrations

# 应用迁移
python manage.py migrate
```

## 环境变量配置（推荐）

为了提高安全性，建议使用环境变量管理敏感配置：

1. 安装 `python-decouple`:
   ```bash
   pip install python-decouple
   ```

2. 创建 `.env` 文件：
   ```
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   DB_NAME=personalservice
   DB_USER=postgres
   DB_PASSWORD=postgres
   DB_HOST=localhost
   DB_PORT=5432
   ```

3. 在 `settings.py` 中使用：
   ```python
   from decouple import config
   
   SECRET_KEY = config('SECRET_KEY')
   DEBUG = config('DEBUG', default=False, cast=bool)
   ```

## 部署注意事项

在生产环境部署时，请注意：

1. 设置 `DEBUG = False`
2. 配置 `ALLOWED_HOSTS`
3. 使用强密码和安全的 `SECRET_KEY`
4. 配置静态文件服务
5. 使用 HTTPS
6. 配置适当的数据库备份策略

## 许可证

本项目采用 MIT 许可证。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题，请通过 GitHub Issues 联系。
