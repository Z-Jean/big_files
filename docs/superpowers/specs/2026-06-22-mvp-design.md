# 大文件上传系统 MVP 设计文档

## 概述

基于需求文档设计的 MVP 实现方案，采用后端优先策略，分 5 个阶段推进开发。

**技术栈**: Next.js 14 + FastAPI + MySQL 8.0 + Docker
**开发策略**: 后端优先，分阶段推进

---

## 一、项目架构

```
upfiles/
├── backend/                    # FastAPI 后端
│   ├── main.py                 # 应用入口
│   ├── config.py               # 配置管理
│   ├── database.py             # 数据库连接
│   ├── dependencies.py         # 依赖注入（JWT）
│   ├── models/                 # 数据模型
│   │   ├── user.py
│   │   ├── file.py
│   │   └── chunk.py
│   ├── routes/                 # API 路由
│   │   ├── auth.py             # 认证接口
│   │   ├── upload.py           # 上传接口
│   │   └── files.py            # 文件管理接口
│   └── services/               # 业务逻辑
│       ├── jwt_service.py      # JWT 生成验证
│       └── upload_service.py   # 分片存储合并
├── frontend/                   # Next.js 前端
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── login/page.tsx
│   │   └── upload/page.tsx
│   └── components/
│       ├── FileUpload.tsx      # 上传组件
│       ├── FileList.tsx        # 文件列表
│       └── ProgressBar.tsx     # 进度条
├── docker-compose.yml          # 服务编排
├── Dockerfile.backend
├── Dockerfile.frontend
└── nginx.conf
```

---

## 二、后端 API 设计

### 认证模块

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/auth/login` | POST | 用户名密码登录，返回 JWT |
| `/api/auth/health` | GET | 健康检查 |

### 上传模块

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/upload/check` | POST | 秒传检测（MD5 查询） |
| `/api/upload/chunks/{md5}` | GET | 查询已上传分片列表 |
| `/api/upload/chunk` | POST | 上传单个分片 |
| `/api/upload/merge` | POST | 合并分片为完整文件 |
| `/api/upload/cancel/{md5}` | DELETE | 取消上传，清理临时文件 |

### 文件管理模块

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/files` | GET | 获取文件列表 |
| `/api/files/{id}` | DELETE | 删除文件 |
| `/api/files/{id}/download` | GET | 下载文件 |

所有接口（除 login 和 health）需要 JWT 认证，通过 `Authorization: Bearer <token>` 传递。

---

## 三、数据库设计

### 三张核心表

```sql
-- 用户表
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 文件表
CREATE TABLE files (
    id INT PRIMARY KEY AUTO_INCREMENT,
    md5 VARCHAR(32) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    user_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_md5 (md5),
    INDEX idx_user_id (user_id)
);

-- 分片表
CREATE TABLE chunks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    file_md5 VARCHAR(32) NOT NULL,
    chunk_index INT NOT NULL,
    status VARCHAR(20) DEFAULT 'uploading',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_chunk (file_md5, chunk_index)
);
```

### 设计要点

| 表 | 关键设计 | 说明 |
|----|----------|------|
| users | username 唯一索引 | 防止重复注册 |
| files | md5 索引 + user_id 索引 | 秒传查询和用户隔离 |
| chunks | (file_md5, chunk_index) 唯一约束 | 防止重复上传同一分片 |

---

## 四、文件存储设计

### 目录结构

```
项目根目录/
├── uploads/                    # 最终合并文件
│   ├── 8a3f.mp4               # 以 MD5 前4位命名
│   └── b2c1.zip
├── chunks/                     # 临时分片
│   ├── a1b2c3d4.../           # 以文件 MD5 命名目录
│   │   ├── 0.chunk
│   │   ├── 1.chunk
│   │   └── 2.chunk
│   └── e5f6g7h8.../
└── mysql_data/                 # MySQL 数据持久化
```

### 存储流程

```
用户选择文件
    ↓
前端计算 MD5
    ↓
分片切割（5MB/片）
    ↓
逐片上传 → chunks/{md5}/
    ↓
全部完成 → 合并 → uploads/
    ↓
清理 chunks/{md5}/ 目录
```

### 安全设计

| 措施 | 说明 |
|------|------|
| MD5 十六进制校验 | 防止路径穿越攻击 |
| 分片大小限制 | 服务端限制最大 5MB |
| 文件大小校验 | 服务端校验不超过 2GB |
| 用户隔离 | 文件按 user_id 过滤 |

---

## 五、前端页面设计

### 页面结构

| 页面 | 路由 | 功能 |
|------|------|------|
| 登录页 | `/login` | 用户名密码登录 |
| 上传页 | `/upload` | 文件上传 + 文件列表 |
| 首页 | `/` | 根据登录状态自动跳转 |

### 组件设计

```
upload/page.tsx
├── Header                    # 顶部栏（用户名 + 退出按钮）
├── FileUpload                # 上传组件
│   ├── 文件选择区域（支持拖拽）
│   ├── 上传队列列表
│   │   ├── 文件名 + 大小
│   │   ├── 状态图标（计算中/上传中/暂停/完成/错误）
│   │   ├── 进度条（百分比 + 速度 + 剩余时间）
│   │   └── 操作按钮（暂停/继续/取消）
│   └── MD5 计算（Web Worker）
└── FileList                  # 文件列表组件
    ├── 文件表格（文件名/大小/上传时间/操作）
    └── 下载/删除按钮
```

### 交互流程

| 步骤 | 用户操作 | 系统响应 |
|------|----------|----------|
| 1 | 点击选择文件或拖拽 | 弹出文件选择框 |
| 2 | 选择文件 | 显示文件列表 + 计算 MD5 |
| 3 | MD5 计算完成 | 检测秒传 → 查询已传分片 |
| 4 | 开始上传 | 显示进度条 + 速度 + 剩余时间 |
| 5 | 可点击暂停 | 暂停上传，保留已传分片 |
| 6 | 可点击继续 | 继续上传剩余分片 |
| 7 | 可点击取消 | 清理临时文件，移除队列 |
| 8 | 上传完成 | 文件出现在文件列表 |
| 9 | 点击下载 | 下载文件到本地 |
| 10 | 点击删除 | 二次确认后删除文件 |

---

## 六、上传核心流程

### 上传状态机

```
idle → calculating → uploading → merging → completed
                    ↓           ↓
                  paused      error
                    ↓
                 uploading
```

### 状态说明

| 状态 | 含义 | 可用操作 |
|------|------|----------|
| idle | 初始状态 | 选择文件 |
| calculating | 计算 MD5 中 | 等待 |
| uploading | 上传分片中 | 暂停/取消 |
| paused | 已暂停 | 继续/取消 |
| merging | 合并中 | 等待 |
| completed | 完成 | 无 |
| error | 出错 | 重试/取消 |

### MD5 计算

```
使用 Web Worker 后台计算，不阻塞 UI：
1. 读取文件（每次 2MB）
2. 送入 spark-md5 计算
3. 返回进度和最终 MD5
```

### 分片上传

```
循环上传缺失分片：
1. file.slice(start, end) 切割 5MB
2. FormData 携带 md5 + chunkIndex + totalChunks + chunk
3. POST /api/upload/chunk
4. 更新进度条
5. 重复直到全部完成
```

### 断点续传

```
页面刷新后重新选择同一文件：
1. 重新计算 MD5
2. GET /api/upload/chunks/{md5} 查询已传分片
3. 跳过已传分片，只传缺失部分
```

---

## 七、Docker 部署设计

### 服务编排

```yaml
# docker-compose.yml
services:
  mysql:
    image: mysql:8.0
    ports: 3306:3306
    volumes:
      - mysql_data:/var/lib/mysql
    environment:
      MYSQL_ROOT_PASSWORD: 123456
      MYSQL_DATABASE: file_upload

  backend:
    build: ./backend
    ports: 8000:8000
    volumes:
      - ./uploads:/app/uploads
      - ./chunks:/app/chunks
    depends_on:
      mysql: { condition: service_healthy }

  frontend:
    build: ./frontend
    ports: 3000:3000
    depends_on:
      - backend

  nginx:
    image: nginx:alpine
    ports: 80:80
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - frontend
      - backend
```

### Nginx 配置

```nginx
client_max_body_size 2G;          # 支持 2GB 文件
proxy_read_timeout 600s;          # 上传超时 10 分钟
proxy_send_timeout 600s;

# 反向代理
location /api/ {
    proxy_pass http://backend:8000;
}
location / {
    proxy_pass http://frontend:3000;
}
```

### 数据持久化

| 数据 | 挂载位置 | 说明 |
|------|----------|------|
| MySQL 数据 | `mysql_data` volume | 数据库持久化 |
| 上传文件 | `./uploads` | 最终文件 |
| 临时分片 | `./chunks` | 上传中的分片 |

---

## 八、分阶段开发计划

### 阶段 1：后端基础（2-3 天）

| 任务 | 内容 | 产出 |
|------|------|------|
| 项目搭建 | FastAPI 项目结构 + 依赖 | 可运行的后端框架 |
| 数据库连接 | SQLAlchemy + MySQL 连接 | 数据库连接正常 |
| 用户模型 | User 表 + bcrypt 密码 | 用户数据存储 |
| JWT 认证 | 令牌生成 + 验证 + 依赖注入 | 登录接口可用 |
| 登录接口 | POST /api/auth/login | 返回 JWT 令牌 |

### 阶段 2：上传核心（3-4 天）

| 任务 | 内容 | 产出 |
|------|------|------|
| 文件模型 | File + Chunk 表 | 文件和分片数据存储 |
| 分片上传 | POST /api/upload/chunk | 分片保存到磁盘 |
| 分片查询 | GET /api/upload/chunks/{md5} | 查询已传分片 |
| 秒传检测 | POST /api/upload/check | MD5 存在性检查 |
| 分片合并 | POST /api/upload/merge | 合并为完整文件 |
| 取消上传 | DELETE /api/upload/cancel/{md5} | 清理临时文件 |

### 阶段 3：文件管理（2 天）

| 任务 | 内容 | 产出 |
|------|------|------|
| 文件列表 | GET /api/files | 返回用户文件列表 |
| 文件下载 | GET /api/files/{id}/download | 下载完整文件 |
| 文件删除 | DELETE /api/files/{id} | 删除文件和记录 |

### 阶段 4：前端开发（3-4 天）

| 任务 | 内容 | 产出 |
|------|------|------|
| 项目搭建 | Next.js 14 + TypeScript + Tailwind | 可运行的前端框架 |
| 登录页面 | 登录表单 + JWT 存储 | 登录功能完整 |
| 上传组件 | 文件选择 + MD5 + 分片上传 | 上传功能完整 |
| 进度显示 | 进度条 + 速度 + 剩余时间 | 用户体验完整 |
| 文件列表 | 文件表格 + 下载 + 删除 | 文件管理完整 |

### 阶段 5：部署上线（1 天）

| 任务 | 内容 | 产出 |
|------|------|------|
| Dockerfile | 后端 + 前端镜像 | 可构建的镜像 |
| Docker Compose | 服务编排 | 一键启动 |
| Nginx 配置 | 反向代理 + 大文件支持 | 访问正常 |
| CI/CD | GitHub Actions | 自动部署 |

---

## 九、错误处理设计

### 后端错误响应

| 错误码 | 场景 | 响应格式 |
|--------|------|----------|
| 400 | 参数缺失/格式错误 | `{"detail": "缺少必要参数"}` |
| 401 | 未认证/token过期 | `{"detail": "未授权"}` |
| 403 | 无权操作他人文件 | `{"detail": "禁止访问"}` |
| 404 | 文件/分片不存在 | `{"detail": "资源不存在"}` |
| 413 | 分片超过5MB | `{"detail": "分片大小超过限制"}` |
| 500 | 服务器内部错误 | `{"detail": "服务器错误"}` |

### 前端错误处理

| 场景 | 处理方式 |
|------|----------|
| 网络错误 | 显示"网络异常，请重试"，保留上传状态 |
| 认证过期 | 自动跳转 /login |
| 分片上传失败 | 自动重试 3 次，失败后显示错误 |
| 合并失败 | 显示"合并失败，请重试" |
| 文件过大 | 前端校验 2GB，提示"文件超过限制" |

### 重试机制

```
分片上传失败时：
1. 自动重试，最多 3 次
2. 每次重试间隔 1 秒
3. 3 次都失败后标记为 error
4. 用户可手动重试或取消
```

---

## 十、安全设计

### 安全措施

| 措施 | 实现方式 | 说明 |
|------|----------|------|
| 密码加密 | bcrypt 哈希 | 不存储明文密码 |
| JWT 认证 | HS256 + 2小时过期 | 所有接口需认证 |
| 路径穿越防护 | MD5 十六进制校验 | 防止 `../../../` 攻击 |
| 文件大小限制 | 前端 2GB + 后端 5MB/片 | 防止内存溢出 |
| 用户隔离 | files 表按 user_id 过滤 | 只能操作自己的文件 |
| 文件名安全 | 上传用 MD5 命名 | 避免特殊字符问题 |

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| MYSQL_HOST | localhost | 数据库地址 |
| MYSQL_PORT | 3306 | 数据库端口 |
| MYSQL_USER | root | 数据库用户 |
| MYSQL_PASSWORD | root | 数据库密码 |
| MYSQL_DB | file_upload | 数据库名 |
| JWT_SECRET | 需要设置 | JWT 密钥 |
| CHUNK_SIZE | 5242880 | 分片大小 5MB |
| MAX_FILE_SIZE | 2147483648 | 最大文件 2GB |

---

## 十一、测试策略

### 测试覆盖

| 类型 | 工具 | 覆盖内容 |
|------|------|----------|
| 后端单元测试 | pytest | JWT 服务、上传服务 |
| 后端接口测试 | pytest + httpx | 所有 API 端点 |
| 前端组件测试 | Jest + React Testing Library | 上传组件、文件列表 |
| E2E 测试 | Playwright | 完整上传流程 |

### 关键测试用例

| 测试场景 | 预期结果 |
|----------|----------|
| 正常登录 | 返回 JWT 令牌 |
| 密码错误 | 返回 401 |
| 分片上传 | 保存到 chunks 目录 |
| 分片合并 | 生成完整文件 |
| 秒传检测 | 返回 instantUpload: true |
| 断点续传 | 跳过已传分片 |
| 文件下载 | 返回完整文件 |
| 文件删除 | 删除记录和文件 |
