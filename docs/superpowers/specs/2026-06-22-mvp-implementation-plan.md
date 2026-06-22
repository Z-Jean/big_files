# 大文件上传系统 MVP 实现计划

## 概述

基于 MVP 设计文档的详细实现计划，分 5 个阶段推进，共约 11-14 天。

**设计文档**: `docs/superpowers/specs/2026-06-22-mvp-design.md`
**开发策略**: 后端优先，分阶段推进

---

## 阶段 1：后端基础（2-3 天）

### 1.1 项目搭建（0.5 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 创建项目目录 | `backend/` | 后端根目录 |
| 2 | 创建虚拟环境 | `backend/.venv` | Python 虚拟环境 |
| 3 | 安装依赖 | `backend/requirements.txt` | fastapi, uvicorn, sqlalchemy, pymysql, python-jose, passlib, bcrypt, python-multipart |
| 4 | 创建配置文件 | `backend/config.py` | 环境变量管理 |
| 5 | 创建数据库连接 | `backend/database.py` | SQLAlchemy 引擎 |
| 6 | 创建应用入口 | `backend/main.py` | FastAPI 应用实例 |

**依赖列表**:
```
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
pymysql==1.1.0
python-jose==3.3.0
passlib==1.7.4
bcrypt==4.0.1
python-multipart==0.0.6
aiofiles==23.2.1
python-dotenv==1.0.0
```

### 1.2 数据库模型（0.5 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 创建用户模型 | `backend/models/user.py` | User 表 |
| 2 | 创建文件模型 | `backend/models/file.py` | File 表 |
| 3 | 创建分片模型 | `backend/models/chunk.py` | Chunk 表 |
| 4 | 创建初始化脚本 | `backend/init_db.py` | 建表 + 默认用户 |

**模型字段**:
```python
# User 模型
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# File 模型
class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True)
    md5 = Column(String(32), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Chunk 模型
class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(Integer, primary_key=True)
    file_md5 = Column(String(32), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    status = Column(String(20), default="uploading")
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('file_md5', 'chunk_index'),)
```

### 1.3 JWT 认证（0.5 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 创建 JWT 服务 | `backend/services/jwt_service.py` | 令牌生成和验证 |
| 2 | 创建认证依赖 | `backend/dependencies.py` | HTTPBearer 依赖注入 |
| 3 | 创建密码哈希工具 | `backend/utils/password.py` | bcrypt 加密 |

**JWT 服务**:
```python
# services/jwt_service.py
from jose import JWTError, jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-secret-key"  # 环境变量
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 2

def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> int:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return int(payload["sub"])
```

### 1.4 登录接口（0.5 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 创建认证路由 | `backend/routes/auth.py` | 登录接口 |
| 2 | 注册路由到应用 | `backend/main.py` | 路由注册 |
| 3 | 创建默认用户 | `backend/main.py` | 启动时创建 admin 用户 |

**登录接口**:
```python
# routes/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login")
def login(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(user.id)
    return {"token": token, "user": {"id": user.id, "username": user.username}}
```

### 阶段 1 验收

- [ ] 后端可以启动：`uvicorn main:app --reload`
- [ ] 数据库连接正常
- [ ] 登录接口可用：`POST /api/auth/login`
- [ ] JWT 令牌可以生成和验证
- [ ] 默认用户 admin/123456 可以登录

---

## 阶段 2：上传核心（3-4 天）

### 2.1 文件模型（0.5 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 完善文件模型 | `backend/models/file.py` | 添加索引 |
| 2 | 完善分片模型 | `backend/models/chunk.py` | 添加唯一约束 |
| 3 | 更新初始化脚本 | `backend/init_db.py` | 创建新表 |

### 2.2 上传服务（1 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 创建上传服务 | `backend/services/upload_service.py` | 分片存储和合并 |
| 2 | 实现分片保存 | `backend/services/upload_service.py` | 保存到 chunks 目录 |
| 3 | 实现分片合并 | `backend/services/upload_service.py` | 合并为完整文件 |
| 4 | 实现文件清理 | `backend/services/upload_service.py` | 删除临时分片 |

**上传服务**:
```python
# services/upload_service.py
import os
import hashlib
from pathlib import Path

CHUNK_DIR = Path("chunks")
UPLOAD_DIR = Path("uploads")

def save_chunk(md5: str, chunk_index: int, chunk_data: bytes) -> str:
    """保存分片到磁盘"""
    chunk_dir = CHUNK_DIR / md5
    chunk_dir.mkdir(parents=True, exist_ok=True)
    chunk_path = chunk_dir / f"{chunk_index}.chunk"
    chunk_path.write_bytes(chunk_data)
    return str(chunk_path)

def merge_chunks(md5: str, filename: str, total_chunks: int) -> str:
    """合并分片为完整文件"""
    chunk_dir = CHUNK_DIR / md5
    upload_dir = UPLOAD_DIR
    upload_dir.mkdir(exist_ok=True)

    # 生成唯一文件名
    file_ext = Path(filename).suffix
    unique_name = hashlib.md5(md5.encode()).hexdigest()[:8] + file_ext
    file_path = upload_dir / unique_name

    # 合并分片
    with open(file_path, "wb") as f:
        for i in range(total_chunks):
            chunk_path = chunk_dir / f"{i}.chunk"
            f.write(chunk_path.read_bytes())

    # 清理分片目录
    import shutil
    shutil.rmtree(chunk_dir)

    return str(file_path)

def delete_chunks(md5: str) -> None:
    """删除分片目录"""
    chunk_dir = CHUNK_DIR / md5
    if chunk_dir.exists():
        import shutil
        shutil.rmtree(chunk_dir)
```

### 2.3 上传接口（1 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 创建上传路由 | `backend/routes/upload.py` | 所有上传接口 |
| 2 | 实现秒传检测 | `backend/routes/upload.py` | POST /api/upload/check |
| 3 | 实现分片查询 | `backend/routes/upload.py` | GET /api/upload/chunks/{md5} |
| 4 | 实现分片上传 | `backend/routes/upload.py` | POST /api/upload/chunk |
| 5 | 实现分片合并 | `backend/routes/upload.py` | POST /api/upload/merge |
| 6 | 实现取消上传 | `backend/routes/upload.py` | DELETE /api/upload/cancel/{md5} |

**上传接口**:
```python
# routes/upload.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/upload", tags=["upload"])

@router.post("/check")
def check_file(md5: str, db: Session = Depends(get_db), user = Depends(get_current_user)):
    """秒传检测"""
    file = db.query(File).filter(File.md5 == md5).first()
    return {"instantUpload": file is not None}

@router.get("/chunks/{md5}")
def get_uploaded_chunks(md5: str, db: Session = Depends(get_db), user = Depends(get_current_user)):
    """查询已上传分片"""
    chunks = db.query(Chunk).filter(
        Chunk.file_md5 == md5,
        Chunk.status == "completed"
    ).all()
    return {"uploadedChunks": [c.chunk_index for c in chunks]}

@router.post("/chunk")
async def upload_chunk(
    md5: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    chunk: UploadFile = File(...),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """上传单个分片"""
    # 验证 MD5 格式
    if not all(c in '0123456789abcdef' for c in md5):
        raise HTTPException(status_code=400, detail="MD5 格式错误")

    # 验证分片大小
    chunk_data = await chunk.read()
    if len(chunk_data) > 5 * 1024 * 1024:  # 5MB
        raise HTTPException(status_code=413, detail="分片大小超过限制")

    # 保存分片
    save_chunk(md5, chunk_index, chunk_data)

    # 更新数据库
    existing = db.query(Chunk).filter(
        Chunk.file_md5 == md5,
        Chunk.chunk_index == chunk_index
    ).first()
    if existing:
        existing.status = "completed"
    else:
        db.add(Chunk(file_md5=md5, chunk_index=chunk_index, status="completed"))
    db.commit()

    return {"success": True}

@router.post("/merge")
def merge_chunks_api(
    md5: str = Form(...),
    filename: str = Form(...),
    total_chunks: int = Form(...),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """合并分片"""
    # 检查是否已存在
    existing_file = db.query(File).filter(File.md5 == md5).first()
    if existing_file:
        return {"success": True, "message": "文件已存在"}

    # 合并文件
    file_path = merge_chunks(md5, filename, total_chunks)

    # 保存到数据库
    file_size = os.path.getsize(file_path)
    new_file = File(
        md5=md5,
        original_filename=filename,
        file_path=file_path,
        file_size=file_size,
        user_id=user.id
    )
    db.add(new_file)
    db.commit()

    return {"success": True}

@router.delete("/cancel/{md5}")
def cancel_upload(md5: str, db: Session = Depends(get_db), user = Depends(get_current_user)):
    """取消上传"""
    delete_chunks(md5)
    db.query(Chunk).filter(Chunk.file_md5 == md5).delete()
    db.commit()
    return {"success": True}
```

### 2.4 安全验证（0.5 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 添加 MD5 格式验证 | `backend/routes/upload.py` | 防止路径穿越 |
| 2 | 添加分片大小限制 | `backend/routes/upload.py` | 防止内存溢出 |
| 3 | 添加用户隔离 | `backend/routes/upload.py` | 只能操作自己的文件 |

### 阶段 2 验收

- [ ] 秒传检测可用：`POST /api/upload/check`
- [ ] 分片查询可用：`GET /api/upload/chunks/{md5}`
- [ ] 分片上传可用：`POST /api/upload/chunk`
- [ ] 分片合并可用：`POST /api/upload/merge`
- [ ] 取消上传可用：`DELETE /api/upload/cancel/{md5}`
- [ ] 安全验证生效（路径穿越防护、大小限制）

---

## 阶段 3：文件管理（2 天）

### 3.1 文件列表接口（0.5 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 创建文件路由 | `backend/routes/files.py` | 文件管理接口 |
| 2 | 实现文件列表 | `backend/routes/files.py` | GET /api/files |

**文件列表接口**:
```python
# routes/files.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/files", tags=["files"])

@router.get("")
def get_files(db: Session = Depends(get_db), user = Depends(get_current_user)):
    """获取文件列表"""
    files = db.query(File).filter(File.user_id == user.id).all()
    return [{
        "id": f.id,
        "filename": f.original_filename,
        "size": f.file_size,
        "url": f"/uploads/{Path(f.file_path).name}",
        "created_at": f.created_at.isoformat()
    } for f in files]
```

### 3.2 文件下载接口（0.5 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 实现文件下载 | `backend/routes/files.py` | GET /api/files/{id}/download |

**文件下载接口**:
```python
@router.get("/{file_id}/download")
def download_file(file_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    """下载文件"""
    file = db.query(File).filter(File.id == file_id, File.user_id == user.id).first()
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(
        path=file.file_path,
        filename=file.original_filename,
        media_type="application/octet-stream"
    )
```

### 3.3 文件删除接口（0.5 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 实现文件删除 | `backend/routes/files.py` | DELETE /api/files/{id} |

**文件删除接口**:
```python
@router.delete("/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    """删除文件"""
    file = db.query(File).filter(File.id == file_id, File.user_id == user.id).first()
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 删除物理文件
    if os.path.exists(file.file_path):
        os.remove(file.file_path)

    # 删除数据库记录
    db.delete(file)
    db.commit()

    return {"success": True}
```

### 3.4 路由注册（0.5 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 注册文件路由 | `backend/main.py` | 路由注册 |
| 2 | 测试所有接口 | - | Postman 或 curl 测试 |

### 阶段 3 验收

- [ ] 文件列表可用：`GET /api/files`
- [ ] 文件下载可用：`GET /api/files/{id}/download`
- [ ] 文件删除可用：`DELETE /api/files/{id}`
- [ ] 用户隔离生效（只能操作自己的文件）

---

## 阶段 4：前端开发（3-4 天）

### 4.1 项目搭建（0.5 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 创建 Next.js 项目 | `frontend/` | `npx create-next-app@14` |
| 2 | 安装依赖 | `frontend/package.json` | spark-md5 |
| 3 | 配置 Tailwind | `frontend/tailwind.config.ts` | 样式配置 |
| 4 | 配置 API 代理 | `frontend/next.config.js` | 代理到后端 |

**API 代理配置**:
```javascript
// next.config.js
module.exports = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
      {
        source: '/uploads/:path*',
        destination: 'http://localhost:8000/uploads/:path*',
      },
    ];
  },
};
```

### 4.2 登录页面（0.5 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 创建登录页面 | `frontend/app/login/page.tsx` | 登录表单 |
| 2 | 实现登录逻辑 | `frontend/app/login/page.tsx` | JWT 存储 |
| 3 | 创建路由守卫 | `frontend/app/upload/page.tsx` | 未登录跳转 |

**登录页面**:
```tsx
// app/login/page.tsx
'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const router = useRouter();

  const handleLogin = async () => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (res.ok) {
      const data = await res.json();
      localStorage.setItem('token', data.token);
      router.push('/upload');
    } else {
      setError('用户名或密码错误');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-md w-96">
        <h1 className="text-2xl font-bold mb-6">登录</h1>
        {error && <p className="text-red-500 mb-4">{error}</p>}
        <input
          type="text"
          placeholder="用户名"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="w-full p-2 border rounded mb-4"
        />
        <input
          type="password"
          placeholder="密码"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full p-2 border rounded mb-4"
        />
        <button
          onClick={handleLogin}
          className="w-full bg-blue-500 text-white p-2 rounded"
        >
          登录
        </button>
      </div>
    </div>
  );
}
```

### 4.3 上传组件（1.5 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 创建上传组件 | `frontend/components/FileUpload.tsx` | 核心上传逻辑 |
| 2 | 实现 MD5 计算 | `frontend/components/FileUpload.tsx` | Web Worker |
| 3 | 实现分片上传 | `frontend/components/FileUpload.tsx` | 循环上传 |
| 4 | 实现暂停/继续 | `frontend/components/FileUpload.tsx` | AbortController |
| 5 | 实现取消上传 | `frontend/components/FileUpload.tsx` | 清理临时文件 |

**上传组件核心逻辑**:
```tsx
// components/FileUpload.tsx
'use client';
import { useState, useRef } from 'react';
import SparkMD5 from 'spark-md5';

interface UploadItem {
  file: File;
  md5: string;
  totalChunks: number;
  uploadedChunks: number[];
  currentChunk: number;
  status: 'idle' | 'calculating' | 'uploading' | 'paused' | 'completed' | 'error';
  progress: number;
}

export default function FileUpload() {
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const isPausedRef = useRef(false);

  // 计算 MD5
  const calculateMD5 = async (file: File): Promise<string> => {
    return new Promise((resolve) => {
      const spark = new SparkMD5.ArrayBuffer();
      const reader = new FileReader();
      const chunkSize = 2 * 1024 * 1024; // 2MB
      let offset = 0;

      const loadChunk = () => {
        const slice = file.slice(offset, offset + chunkSize);
        reader.readAsArrayBuffer(slice);
      };

      reader.onload = (e) => {
        spark.append(e.target?.result as ArrayBuffer);
        offset += chunkSize;
        if (offset < file.size) {
          loadChunk();
        } else {
          resolve(spark.end());
        }
      };

      loadChunk();
    });
  };

  // 上传分片
  const uploadChunk = async (item: UploadItem, chunkIndex: number) => {
    const start = chunkIndex * 5 * 1024 * 1024;
    const end = Math.min(start + 5 * 1024 * 1024, item.file.size);
    const chunk = item.file.slice(start, end);

    const formData = new FormData();
    formData.append('md5', item.md5);
    formData.append('chunk_index', chunkIndex.toString());
    formData.append('total_chunks', item.totalChunks.toString());
    formData.append('chunk', chunk);

    const token = localStorage.getItem('token');
    const res = await fetch('/api/upload/chunk', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData,
    });

    if (!res.ok) throw new Error('上传失败');
  };

  // 上传文件
  const uploadFile = async (item: UploadItem) => {
    for (let i = item.currentChunk; i < item.totalChunks; i++) {
      if (isPausedRef.current) {
        setUploads(prev => prev.map(u =>
          u.md5 === item.md5 ? { ...u, status: 'paused', currentChunk: i } : u
        ));
        return;
      }

      try {
        await uploadChunk(item, i);
        setUploads(prev => prev.map(u =>
          u.md5 === item.md5 ? {
            ...u,
            currentChunk: i + 1,
            progress: ((i + 1) / u.totalChunks) * 100
          } : u
        ));
      } catch (error) {
        setUploads(prev => prev.map(u =>
          u.md5 === item.md5 ? { ...u, status: 'error' } : u
        ));
        return;
      }
    }

    // 合并文件
    await mergeChunks(item);
    setUploads(prev => prev.map(u =>
      u.md5 === item.md5 ? { ...u, status: 'completed', progress: 100 } : u
    ));
  };

  return (
    <div>
      <input
        type="file"
        multiple
        onChange={handleFileSelect}
        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
      />
      <div className="mt-4">
        {uploads.map((item) => (
          <div key={item.md5} className="border p-4 mb-2 rounded">
            <p>{item.file.name} ({formatSize(item.file.size)})</p>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div
                className="bg-blue-600 h-2.5 rounded-full"
                style={{ width: `${item.progress}%` }}
              />
            </div>
            <p>{item.progress.toFixed(1)}% - {item.status}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 4.4 进度显示（0.5 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 创建进度条组件 | `frontend/components/ProgressBar.tsx` | 进度条 |
| 2 | 添加速度计算 | `frontend/components/ProgressBar.tsx` | MB/s |
| 3 | 添加剩余时间 | `frontend/components/ProgressBar.tsx` | 预计时间 |

### 4.5 文件列表（0.5 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 创建文件列表组件 | `frontend/components/FileList.tsx` | 文件表格 |
| 2 | 实现下载功能 | `frontend/components/FileList.tsx` | Blob 下载 |
| 3 | 实现删除功能 | `frontend/components/FileList.tsx` | 确认对话框 |

### 4.6 上传页面（0.5 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 创建上传页面 | `frontend/app/upload/page.tsx` | 组合组件 |
| 2 | 添加路由守卫 | `frontend/app/upload/page.tsx` | 未登录跳转 |
| 3 | 添加退出按钮 | `frontend/app/upload/page.tsx` | 清除 token |

### 阶段 4 验收

- [ ] 登录页面可用
- [ ] 上传页面可用
- [ ] 文件选择和 MD5 计算正常
- [ ] 分片上传正常
- [ ] 进度条显示正常
- [ ] 暂停/继续/取消功能正常
- [ ] 文件列表显示正常
- [ ] 下载和删除功能正常

---

## 阶段 5：部署上线（1 天）

### 5.1 Dockerfile（0.5 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 创建后端 Dockerfile | `Dockerfile.backend` | Python 镜像 |
| 2 | 创建前端 Dockerfile | `Dockerfile.frontend` | Node.js 镜像 |

**后端 Dockerfile**:
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
COPY . .
RUN mkdir -p uploads chunks
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**前端 Dockerfile**:
```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

### 5.2 Docker Compose（0.25 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 创建 docker-compose.yml | `docker-compose.yml` | 服务编排 |

**docker-compose.yml**:
```yaml
services:
  mysql:
    image: mysql:8.0
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    environment:
      MYSQL_ROOT_PASSWORD: 123456
      MYSQL_DATABASE: file_upload
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./uploads:/app/uploads
      - ./chunks:/app/chunks
    environment:
      MYSQL_HOST: mysql
      MYSQL_PORT: 3306
      MYSQL_USER: root
      MYSQL_PASSWORD: 123456
      MYSQL_DB: file_upload
      JWT_SECRET: your-secret-key-here
    depends_on:
      mysql:
        condition: service_healthy

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - frontend
      - backend

volumes:
  mysql_data:
```

### 5.3 Nginx 配置（0.125 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 创建 Nginx 配置 | `nginx.conf` | 反向代理 |

**nginx.conf**:
```nginx
worker_processes auto;
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    client_max_body_size 2G;
    client_body_timeout 600s;
    client_header_timeout 600s;

    upstream frontend {
        server frontend:3000;
    }

    upstream backend {
        server backend:8000;
    }

    server {
        listen 80;

        location /api/ {
            proxy_pass http://backend;
            proxy_read_timeout 600s;
            proxy_send_timeout 600s;
        }

        location /uploads/ {
            proxy_pass http://backend;
        }

        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
        }
    }
}
```

### 5.4 CI/CD（0.125 天）

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 创建 GitHub Actions | `.github/workflows/ci.yml` | 自动部署 |

**CI/CD 配置**:
```yaml
# .github/workflows/ci.yml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r backend/requirements.txt
      - run: python -m py_compile backend/main.py

  frontend-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: cd frontend && npm ci && npm run build

  deploy:
    needs: [backend-check, frontend-check]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USERNAME }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          script: |
            cd /path/to/project
            git pull
            docker-compose down
            docker-compose up -d --build
```

### 阶段 5 验收

- [ ] Docker Compose 可以启动所有服务
- [ ] 前端可以通过 http://localhost 访问
- [ ] 后端 API 可以正常调用
- [ ] 文件上传和下载正常
- [ ] GitHub Actions 可以自动部署

---

## 开发时间总结

| 阶段 | 任务 | 时间 |
|------|------|------|
| 阶段 1 | 后端基础 | 2-3 天 |
| 阶段 2 | 上传核心 | 3-4 天 |
| 阶段 3 | 文件管理 | 2 天 |
| 阶段 4 | 前端开发 | 3-4 天 |
| 阶段 5 | 部署上线 | 1 天 |
| **总计** | | **11-14 天** |

---

## 关键依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 后端运行环境 |
| Node.js | 18+ | 前端运行环境 |
| MySQL | 8.0 | 数据库 |
| Docker | latest | 容器化部署 |
| Git | latest | 版本控制 |

---

## 风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| MySQL 连接问题 | 后端无法启动 | 检查配置，使用 Docker 网络 |
| 大文件上传超时 | 上传失败 | 增加 Nginx 超时时间 |
| MD5 计算慢 | 用户体验差 | 使用 Web Worker 后台计算 |
| 分片合并失败 | 文件损坏 | 添加分片完整性校验 |
| 跨域问题 | 前端无法调用 API | 配置 CORS 或使用代理 |
