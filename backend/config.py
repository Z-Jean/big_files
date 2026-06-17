import os

# 获取项目根目录（backend 的上一级目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Settings:
    # 数据库
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "root")
    MYSQL_DB: str = os.getenv("MYSQL_DB", "file_upload")

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-secret-key-here")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 2

    # 上传
    CHUNK_SIZE: int = 5 * 1024 * 1024  # 5MB
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "uploads")
    CHUNK_DIR: str = os.path.join(BASE_DIR, "chunks")
    MAX_FILE_SIZE: int = 2 * 1024 * 1024 * 1024  # 2GB

settings = Settings()
