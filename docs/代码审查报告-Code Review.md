# 代码审查报告

**审查日期**: 2026-06-22
**审查范围**: 全项目代码（backend/ + frontend/）
**审查方法**: 8 维度独立扫描 × 候选验证

---

## 审查结果摘要

| 严重程度 | 数量 | 说明 |
|----------|------|------|
| 严重 | 3 | 安全漏洞、数据损坏风险 |
| 高 | 4 | 功能异常、用户体验严重受损 |
| 中 | 3 | 性能问题、潜在崩溃 |
| **合计** | **10** | |

---

## 严重问题（3个）

### C1: 路径穿越漏洞

| 字段 | 内容 |
|------|------|
| 文件 | `backend/services/upload_service.py:11` |
| 严重程度 | 严重 |
| 类型 | 安全漏洞 |

**问题描述**: 用户提供的 `md5` 参数未经验证直接用于 `os.path.join` 构造文件路径。

**失败场景**: 攻击者发送 `md5='../../../etc/passwd'`，导致 `save_chunk` 将分片数据写入任意文件系统位置，可覆盖系统文件或写入恶意内容。

---

### C2: 无分片大小限制导致内存耗尽

| 字段 | 内容 |
|------|------|
| 文件 | `backend/routes/upload.py:64` |
| 严重程度 | 严重 |
| 类型 | 拒绝服务攻击 |

**问题描述**: `chunk.read()` 将整个上传内容读入内存，无大小限制验证。

**失败场景**: 攻击者发送 10GB 的单个分片请求，服务器分配 10GB 内存导致 OOM 崩溃，影响所有并发上传用户。

---

### C3: JWT 密钥硬编码默认值

| 字段 | 内容 |
|------|------|
| 文件 | `backend/config.py:15` |
| 严重程度 | 严重 |
| 类型 | 安全漏洞 |

**问题描述**: `JWT_SECRET` 默认值为 `'your-secret-key-here'`，若未设置环境变量，攻击者可伪造任意用户的 JWT 令牌。

**失败场景**: 生产环境未配置 `JWT_SECRET`，攻击者读取源码后伪造 admin 用户的 JWT，获得系统完全控制权。

---

## 高级问题（4个）

### H1: 分片上传无输入验证

| 字段 | 内容 |
|------|------|
| 文件 | `backend/routes/upload.py:53-87` |
| 严重程度 | 高 |
| 类型 | 安全漏洞 |

**问题描述**: `upload_chunk` 端点未验证 `md5` 格式（应为32位十六进制）、`chunk_index` 范围、`total_chunks` 一致性。

**失败场景**: 非十六进制的 md5 字符串可创建任意目录名；负数 chunk_index 导致索引错误；恶意 chunk_index 可访问其他用户的分片目录。

---

### H2: 合并文件竞态条件

| 字段 | 内容 |
|------|------|
| 文件 | `backend/routes/upload.py:99-103` + `backend/services/upload_service.py:20-55` |
| 严重程度 | 高 |
| 类型 | 数据损坏 |

**问题描述**: `merge_chunks` 路由检查文件存在性与实际创建文件之间无原子性保证，无锁机制。

**失败场景**: 两个用户同时上传相同 MD5 的文件，均通过存在性检查，均执行合并，导致数据库产生重复记录，后写入的文件覆盖先写入的文件。

---

### H3: 前端 API 响应未验证

| 字段 | 内容 |
|------|------|
| 文件 | `frontend/components/FileUpload.tsx:100-105, 141-153` |
| 严重程度 | 高 |
| 类型 | 功能异常 |

**问题描述**: `checkFileExists` 和 `mergeChunks` 未检查 `response.ok`，401/500 错误响应被当作成功处理。

**失败场景**: JWT 过期时，`checkFileExists` 返回错误详情但前端将其视为"文件不存在"，继续无意义的上传；合并失败时前端显示"完成"但文件实际未合并，用户看到绿色对勾却找不到文件。

---

### H4: 恢复上传竞态条件

| 字段 | 内容 |
|------|------|
| 文件 | `frontend/components/FileUpload.tsx:368-370` |
| 严重程度 | 高 |
| 类型 | 功能异常 |

**问题描述**: `handleResume` 使用 `setTimeout(100ms)` 等待 React 状态更新，但无法保证状态已刷新。

**失败场景**: 用户点击继续上传，100ms 内 React 未完成状态更新，`uploadAllFiles` 读取旧状态找不到空闲文件，上传静默失败，用户需再次点击。

---

## 中级问题（3个）

### M1: 异步函数中阻塞式 I/O

| 字段 | 内容 |
|------|------|
| 文件 | `backend/services/upload_service.py:9, 20` |
| 严重程度 | 中 |
| 类型 | 性能问题 |

**问题描述**: `save_chunk` 和 `merge_chunks` 声明为 `async def` 但使用同步的 `open()`/`write()`，阻塞 asyncio 事件循环。

**失败场景**: 10 个并发分片上传各阻塞事件循环 50-200ms，累计阻塞 500ms-2s，期间所有 API 请求（包括健康检查）超时，Docker 标记容器不健康并重启。

---

### M2: 前端上传竞态条件

| 字段 | 内容 |
|------|------|
| 文件 | `frontend/components/FileUpload.tsx:210` |
| 严重程度 | 中 |
| 类型 | 数据一致性 |

**问题描述**: `uploadFile` 中 `uploadedChunks` 使用闭包捕获的变量而非最新状态，`setUploadQueue` 更新器使用外层闭包变量而非 `item.uploadedChunks`。

**失败场景**: 当前顺序执行下恰好正确（每次闭包捕获相同初始数组），但若改为并行上传或 React 批处理行为变化，已上传分片记录丢失，导致重复上传。

---

### M3: 后端文件大小未限制

| 字段 | 内容 |
|------|------|
| 文件 | `backend/routes/upload.py:53` |
| 严重程度 | 中 |
| 类型 | 安全漏洞 |

**问题描述**: `config.py` 定义了 `MAX_FILE_SIZE`（2GB），但无任何路由处理器使用此配置进行服务端验证，仅前端有检查。

**失败场景**: 攻击者绕过前端直接调用 API，发送超大分片，耗尽服务器磁盘空间，所有用户上传失败。

---

## 修复建议优先级

| 优先级 | 问题 | 建议方案 |
|--------|------|----------|
| P0 | C1 路径穿越 | 添加 md5 格式验证：`re.match(r'^[a-f0-9]{32}$', md5)` |
| P0 | C2 内存耗尽 | 分片上传时验证大小：`if len(chunk_data) > CHUNK_SIZE: raise HTTPException(413)` |
| P0 | C3 JWT 密钥 | 生产环境强制配置 JWT_SECRET，启动时检查是否为默认值 |
| P1 | H1 输入验证 | 为 md5、chunk_index、total_chunks 添加格式和范围验证 |
| P1 | H2 合并竞态 | 使用数据库唯一索引 + `INSERT ... ON DUPLICATE KEY UPDATE` |
| P1 | H3 响应验证 | 所有 fetch 调用添加 `if (!response.ok) throw new Error(...)` |
| P1 | H4 恢复竞态 | 使用 `useEffect` 监听状态变化替代 setTimeout |
| P2 | M1 阻塞 I/O | 使用 `aiofiles` 替代同步 `open()`/`write()` |
| P2 | M2 闭包问题 | 使用 `useRef` 存储最新状态，或使用 `useReducer` |
| P2 | M3 文件大小 | 在路由处理器中添加服务端大小验证 |

---

## 附录：其他发现（未验证）

以下为扫描阶段发现但未进入最终验证的候选问题，供参考：

- `backend/init_db.py:26` - SQL 注入（f-string 拼接数据库名）
- `backend/main.py:36` - 硬编码 admin 密码 `123456`
- `backend/main.py:14-20` - CORS 硬编码 `localhost:3000`
- `backend/database.py:7` - 数据库密码未 URL 编码
- `frontend/components/FileUpload.tsx:197` - 进度计算未考虑最后一片大小
- `frontend/components/FileUpload.tsx:202` - 除零风险（speed=0）
- `frontend/components/FileList.tsx:92` - 下载大文件加载整个 Blob 到内存
- `frontend/components/FileUpload.tsx:259` - Promise-inside-setState 反模式
- `backend/services/upload_service.py:27` - MD5 的 MD5 冗余哈希
- `deploy.sh:20` - docker image prune 影响所有容器
