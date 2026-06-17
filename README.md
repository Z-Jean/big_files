# 大文件分片上传系统

企业级大文件资源管理系统，支持分片上传、断点续传、秒传等功能。

## 技术栈

- **前端**：Next.js 14、React、TypeScript、Tailwind CSS
- **后端**：FastAPI、Python 3.10+、SQLAlchemy
- **数据库**：MySQL 8.0
- **容器化**：Docker、Docker Compose
- **CI/CD**：GitHub Actions

## 功能特性

### 1. JWT 登录认证
- 用户名密码登录
- JWT 令牌生成与验证
- 路由守卫保护

### 2. 大文件分片上传
- 文件自动分片（5MB/片）
- 支持最大 2GB 单文件上传
- 实时上传进度显示
- 上传速度和剩余时间计算

### 3. 断点续传
- 网络中断后自动续传
- 跳过已上传分片
- 页面刷新后可继续上传

### 4. 秒传功能
- 基于 MD5 文件哈希
- 相同文件无需重复上传
- 即时完成上传

### 5. 暂停/继续/取消
- 支持暂停上传
- 支持继续上传
- 支持取消上传并清理

## 快速开始

### 方式一：本地开发

#### 1. 启动后端

**使用 uv（推荐，更快）**

```bash
# 进入后端目录
cd backend

# 创建虚拟环境并安装依赖（uv 会自动创建 venv）
uv sync

# 或者手动创建虚拟环境
uv venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows

# 安装依赖
uv pip install -r requirements.txt

# 初始化数据库
uv run python init_db.py

# 启动后端服务
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**使用传统 pip**

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python init_db.py

# 启动后端服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. 启动前端

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动前端服务
npm run dev
```

#### 3. 访问应用

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

### 方式二：Docker 部署（推荐）

#### 1. 一键启动

```bash
# 在项目根目录执行
docker-compose up -d
```

#### 2. 访问应用

- 应用入口：http://localhost（通过 Nginx）
- 前端：http://localhost:3000
- 后端 API：http://localhost:8000

#### 3. 停止服务

```bash
docker-compose down
```

#### 4. 清理数据

```bash
docker-compose down -v
```

## 默认账号

- **用户名**：admin
- **密码**：123456

## 项目结构

```
file-upload-system/
├── backend/                 # 后端代码
│   ├── main.py             # FastAPI 应用入口
│   ├── config.py           # 配置文件
│   ├── database.py         # 数据库连接
│   ├── models/             # 数据模型
│   ├── routes/             # 路由
│   ├── services/           # 业务逻辑
│   └── requirements.txt    # Python 依赖
├── frontend/                # 前端代码
│   ├── app/                # Next.js 页面
│   ├── components/         # React 组件
│   ├── public/             # 静态资源
│   └── package.json        # Node.js 依赖
├── uploads/                 # 上传文件存储
├── chunks/                  # 分片临时存储
├── docker-compose.yml      # Docker 编排配置
├── Dockerfile.backend      # 后端 Dockerfile
├── Dockerfile.frontend     # 前端 Dockerfile
├── nginx.conf              # Nginx 配置
├── init.sql                # 数据库初始化脚本
└── .github/workflows/ci.yml # CI/CD 配置
```

## API 接口

### 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/login | 用户登录 |
| GET | /api/auth/health | 健康检查 |

### 上传接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/upload/check | 秒传检测 |
| GET | /api/upload/chunks/{md5} | 查询已上传分片 |
| POST | /api/upload/chunk | 上传分片 |
| POST | /api/upload/merge | 合并分片 |
| DELETE | /api/upload/cancel/{md5} | 取消上传 |

### 文件接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/files | 获取文件列表 |

## 开发说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| MYSQL_HOST | localhost | MySQL 主机 |
| MYSQL_PORT | 3306 | MySQL 端口 |
| MYSQL_USER | root | MySQL 用户名 |
| MYSQL_PASSWORD | 123456 | MySQL 密码 |
| MYSQL_DB | file_upload | 数据库名 |
| JWT_SECRET | your-secret-key-here | JWT 密钥 |

### 上传限制

- 单文件最大：2GB
- 分片大小：5MB
- 上传超时：600秒

## License

MIT
