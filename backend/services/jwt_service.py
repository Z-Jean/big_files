from datetime import datetime, timedelta
from jose import JWTError, jwt
from config import settings

def create_access_token(user_id: int) -> str:
    """创建 JWT 访问令牌"""
    expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def verify_token(token: str) -> int:
    """验证 JWT 令牌并返回用户 ID"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise JWTError
        return int(user_id)
    except JWTError:
        raise ValueError("无效的令牌")
