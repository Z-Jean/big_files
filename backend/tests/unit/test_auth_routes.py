"""认证路由单元测试"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """创建测试客户端"""
    from main import app
    return TestClient(app)


class TestLogin:
    """登录接口测试"""

    def test_login_success(self, client):
        """测试：正确用户名密码登录成功"""
        response = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "123456"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["username"] == "admin"

    def test_login_wrong_password(self, client):
        """测试：错误密码登录失败"""
        response = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """测试：不存在的用户登录失败"""
        response = client.post("/api/auth/login", json={
            "username": "nonexistent",
            "password": "123456"
        })
        assert response.status_code == 401

    def test_login_empty_credentials(self, client):
        """测试：空凭证登录失败"""
        response = client.post("/api/auth/login", json={
            "username": "",
            "password": ""
        })
        assert response.status_code in [400, 422]

    def test_login_returns_jwt_token(self, client):
        """测试：登录返回有效的 JWT 令牌"""
        response = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "123456"
        })
        token = response.json()["token"]

        # 验证令牌可以解码
        from services.jwt_service import verify_token
        user_id = verify_token(token)
        assert user_id == 1


class TestHealthCheck:
    """健康检查接口测试"""

    def test_health_check(self, client):
        """测试：健康检查返回正常"""
        response = client.get("/api/auth/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestPasswordSecurity:
    """密码安全性测试"""

    def test_password_is_hashed(self):
        """测试：密码使用 bcrypt 加密存储"""
        from models.user import User
        from database import SessionLocal

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == "admin").first()
            # 密码不应该是明文
            assert user.password_hash != "123456"
            # 密码应该是 bcrypt 哈希
            assert user.password_hash.startswith("$2b$")
        finally:
            db.close()

    def test_default_admin_password_is_weak(self):
        """测试：默认 admin 密码是弱密码（安全问题）"""
        # 这个测试提醒：生产环境应该修改默认密码
        default_password = "123456"
        assert len(default_password) < 8  # 不符合强密码要求
