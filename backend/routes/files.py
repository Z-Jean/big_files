from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user
from models.file import File as FileModel
from models.user import User
import os

router = APIRouter()

@router.get("")
async def get_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户上传的文件列表"""
    files = db.query(FileModel).filter(
        FileModel.user_id == current_user.id
    ).order_by(FileModel.created_at.desc()).all()

    file_list = []
    for file in files:
        # 处理 Windows 路径分隔符
        filename = file.file_path.replace('\\', '/').split('/')[-1]
        file_list.append({
            "id": file.id,
            "filename": file.original_filename,
            "file_size": file.file_size,
            "mime_type": file.mime_type,
            "url": f"/uploads/{filename}",
            "created_at": file.created_at.isoformat() if file.created_at else None
        })

    return {"files": file_list}

@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除文件"""
    # 查找文件
    file = db.query(FileModel).filter(
        FileModel.id == file_id,
        FileModel.user_id == current_user.id
    ).first()

    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 删除物理文件
    if os.path.exists(file.file_path):
        os.remove(file.file_path)

    # 删除数据库记录
    db.delete(file)
    db.commit()

    return {"success": True, "message": "文件删除成功"}

@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """下载文件（保持原始文件名）"""
    # 查找文件
    file = db.query(FileModel).filter(
        FileModel.id == file_id,
        FileModel.user_id == current_user.id
    ).first()

    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 检查文件是否存在
    if not os.path.exists(file.file_path):
        raise HTTPException(status_code=404, detail="文件已被删除")

    # 返回文件，使用原始文件名
    return FileResponse(
        path=file.file_path,
        filename=file.original_filename,
        media_type='application/octet-stream'
    )
