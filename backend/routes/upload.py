from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user
from services import upload_service
from models.chunk import Chunk
from models.file import File as FileModel
from models.user import User
from config import settings
import os

router = APIRouter()

@router.post("/check")
async def check_file(
    md5: str,
    file_size: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """秒传检测"""
    existing_file = db.query(FileModel).filter(FileModel.md5 == md5).first()
    if existing_file:
        return {"exists": True, "file_id": existing_file.id, "message": "文件已存在，秒传成功"}
    return {"exists": False, "message": "文件不存在，需要上传"}

@router.get("/chunks/{md5}")
async def get_uploaded_chunks(
    md5: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """查询已上传分片"""
    chunks = db.query(Chunk).filter(
        Chunk.file_md5 == md5,
        Chunk.status == "completed"
    ).all()

    # 检查分片文件是否实际存在
    uploaded_indices = []
    for chunk in chunks:
        chunk_path = os.path.join(settings.CHUNK_DIR, md5, f"{chunk.chunk_index}.chunk")
        if os.path.exists(chunk_path):
            uploaded_indices.append(chunk.chunk_index)
        else:
            # 分片文件不存在，删除数据库记录
            db.delete(chunk)

    db.commit()

    return {"uploaded_chunks": uploaded_indices}

@router.post("/chunk")
async def upload_chunk(
    md5: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    chunk: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """上传单个分片"""
    # 读取分片数据
    chunk_data = await chunk.read()

    # 保存分片
    await upload_service.save_chunk(md5, chunk_index, chunk_data)

    # 更新数据库记录（如果已存在则更新状态）
    existing_chunk = db.query(Chunk).filter(
        Chunk.file_md5 == md5,
        Chunk.chunk_index == chunk_index
    ).first()

    if existing_chunk:
        existing_chunk.status = "completed"
    else:
        chunk_record = Chunk(
            file_md5=md5,
            chunk_index=chunk_index,
            status="completed"
        )
        db.add(chunk_record)

    db.commit()

    return {"success": True, "chunk_index": chunk_index, "message": "分片上传成功"}

@router.post("/merge")
async def merge_chunks(
    md5: str = Form(...),
    filename: str = Form(...),
    total_chunks: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """合并分片"""
    # 检查是否已存在相同文件
    existing_file = db.query(FileModel).filter(FileModel.md5 == md5).first()
    if existing_file:
        return {"success": True, "file_id": existing_file.id, "message": "文件已存在，秒传成功"}

    file_record = await upload_service.merge_chunks(md5, filename, total_chunks, current_user.id, db)
    return {"success": True, "file_id": file_record.id, "message": "文件合并成功"}

@router.delete("/cancel/{md5}")
async def cancel_upload(
    md5: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """取消上传，清理分片"""
    # 删除临时分片
    await upload_service.delete_chunks(md5)

    # 删除数据库记录
    db.query(Chunk).filter(Chunk.file_md5 == md5).delete()
    db.commit()

    return {"success": True, "message": "上传已取消，分片已清理"}
