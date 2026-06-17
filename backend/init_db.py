import pymysql
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base
from models.user import User
from passlib.context import CryptContext
from config import settings

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_database_if_not_exists():
    """如果数据库不存在则创建"""
    try:
        # 连接到 MySQL（不指定数据库）
        connection = pymysql.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            charset='utf8mb4'
        )

        cursor = connection.cursor()

        # 创建数据库
        cursor.execute(f"""
            CREATE DATABASE IF NOT EXISTS {settings.MYSQL_DB}
            CHARACTER SET utf8mb4
            COLLATE utf8mb4_unicode_ci
        """)

        connection.commit()
        cursor.close()
        connection.close()
        print(f"✅ 数据库 {settings.MYSQL_DB} 已就绪")
        return True
    except Exception as e:
        print(f"❌ 创建数据库失败: {e}")
        return False

def init_database():
    """初始化数据库，创建表和默认用户"""
    # 先创建数据库
    if not create_database_if_not_exists():
        return

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    # 创建会话
    db = SessionLocal()

    try:
        # 检查是否已存在 admin 用户
        existing_user = db.query(User).filter(User.username == "admin").first()
        if not existing_user:
            # 创建默认 admin 用户
            admin_user = User(
                username="admin",
                password_hash=pwd_context.hash("123456")
            )
            db.add(admin_user)
            db.commit()
            print("✅ 默认用户创建成功: admin / 123456")
        else:
            print("ℹ️  用户 admin 已存在")
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
