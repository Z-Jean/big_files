import os
import hashlib
import shutil
from sqlalchemy.orm import Session
from models.chunk import Chunk
from models.file import File
from config import settings

async def save_chunk(md5: str, chunk_index: int, chunk_data: bytes) -> str:
    """保存分片到临时目录"""
    chunk_dir = os.path.join(settings.CHUNK_DIR, md5)
    os.makedirs(chunk_dir, exist_ok=True)

    chunk_path = os.path.join(chunk_dir, f"{chunk_index}.chunk")
    with open(chunk_path, "wb") as f:
        f.write(chunk_data)

    return chunk_path

async def merge_chunks(md5: str, filename: str, total_chunks: int, user_id: int, db: Session) -> File:
    """合并分片为完整文件"""
    # 确保上传目录存在
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # 生成唯一文件名
    file_ext = os.path.splitext(filename)[1]
    unique_filename = f"{hashlib.md5(md5.encode()).hexdigest()}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    # 按顺序合并分片
    with open(file_path, "wb") as f:
        for i in range(total_chunks):
            chunk_path = os.path.join(settings.CHUNK_DIR, md5, f"{i}.chunk")
            with open(chunk_path, "rb") as chunk:
                f.write(chunk.read())

    # 获取文件大小
    file_size = os.path.getsize(file_path)

    # 保存文件记录到数据库
    file_record = File(
        md5=md5,
        original_filename=filename,
        file_path=file_path,
        file_size=file_size,
        user_id=user_id
    )
    db.add(file_record)
    db.commit()

    # 清理临时分片
    chunk_dir = os.path.join(settings.CHUNK_DIR, md5)
    shutil.rmtree(chunk_dir, ignore_errors=True)

    return file_record

async def delete_chunks(md5: str):
    """删除临时分片"""
    chunk_dir = os.path.join(settings.CHUNK_DIR, md5)
    shutil.rmtree(chunk_dir, ignore_errors=True)
