# Quick Start Guide

## 快速开始指南 / Quick Start

### English

This is a Django-based web server configured to work with PostgreSQL and accept connections from any external network.

**Quick Start:**

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start PostgreSQL (using Docker):
   ```bash
   docker-compose up -d
   ```

3. Run migrations:
   ```bash
   python manage.py migrate
   ```

4. Start the server:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

5. Access the server:
   - Index: http://your-server-ip:8000/
   - Health Check: http://your-server-ip:8000/health/
   - Admin: http://your-server-ip:8000/admin/

**Verify Configuration:**
```bash
python test_config.py
```

### 中文

这是一个基于Django的Web服务器，配置为使用PostgreSQL数据库并接受来自任何外部网络的连接。

**快速启动：**

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

2. 启动PostgreSQL（使用Docker）：
   ```bash
   docker-compose up -d
   ```

3. 运行数据库迁移：
   ```bash
   python manage.py migrate
   ```

4. 启动服务器：
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

5. 访问服务器：
   - 首页: http://your-server-ip:8000/
   - 健康检查: http://your-server-ip:8000/health/
   - 管理后台: http://your-server-ip:8000/admin/

**验证配置：**
```bash
python test_config.py
```

## Key Features / 主要特性

- ✓ Django 6.0 framework / Django 6.0 框架
- ✓ PostgreSQL database / PostgreSQL 数据库
- ✓ External network access (ALLOWED_HOSTS='*') / 外部网络访问
- ✓ Environment-based configuration / 基于环境变量的配置
- ✓ Docker Compose support / Docker Compose 支持
- ✓ Health check endpoint / 健康检查端点
