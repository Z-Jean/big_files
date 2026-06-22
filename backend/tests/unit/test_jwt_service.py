"""JWT 服务单元测试"""
import pytest
from datetime import datetime, timedelta
from jose import jwt


class TestCreateAccessToken:
    """JWT 令牌生成测试"""

    def test_create_token_success(self):
        """测试：正常生成 JWT 令牌"""
        from services.jwt_service import create_access_token

        user_id = 1
        token = create_access_token(user_id)

        # 验证令牌是字符串
        assert isinstance(token, str)
        # 验证令牌可以解码
        payload = jwt.decode(token, "your-secret-key-here", algorithms=["HS256"])
        assert payload["sub"] == str(user_id)

    def test_create_token_contains_expiry(self):
        """测试：JWT 令牌包含过期时间"""
        from services.jwt_service import create_access_token

        token = create_access_token(1)
        payload = jwt.decode(token, "your-secret-key-here", algorithms=["HS256"])

        # 验证包含 exp 字段
        assert "exp" in payload

    def test_create_token_with_different_users(self):
        """测试：不同用户生成不同令牌"""
        from services.jwt_service import create_access_token

        token1 = create_access_token(1)
        token2 = create_access_token(2)

        payload1 = jwt.decode(token1, "your-secret-key-here", algorithms=["HS256"])
        payload2 = jwt.decode(token2, "your-secret-key-here", algorithms=["HS256"])

        assert payload1["sub"] != payload2["sub"]


class TestVerifyToken:
    """JWT 令牌验证测试"""

    def test_verify_valid_token(self):
        """测试：验证有效令牌"""
        from services.jwt_service import create_access_token, verify_token

        user_id = 42
        token = create_access_token(user_id)
        result = verify_token(token)

        assert result == user_id

    def test_verify_expired_token(self):
        """测试：验证过期令牌"""
        from services.jwt_service import verify_token

        # 创建一个已过期的令牌
        payload = {
            "sub": "1",
            "exp": datetime.utcnow() - timedelta(hours=1)
        }
        token = jwt.encode(payload, "your-secret-key-here", algorithm="HS256")

        with pytest.raises(ValueError, match="无效的令牌"):
            verify_token(token)

    def test_verify_invalid_signature(self):
        """测试：验证签名错误的令牌"""
        from services.jwt_service import verify_token

        # 使用错误的密钥签名
        payload = {"sub": "1", "exp": datetime.utcnow() + timedelta(hours=1)}
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")

        with pytest.raises(ValueError, match="无效的令牌"):
            verify_token(token)

    def test_verify_malformed_token(self):
        """测试：验证格式错误的令牌"""
        from services.jwt_service import verify_token

        with pytest.raises(ValueError, match="无效的令牌"):
            verify_token("not-a-valid-jwt-token")

    def test_verify_token_with_missing_sub(self):
        """测试：验证缺少 sub 字段的令牌"""
        from services.jwt_service import verify_token

        payload = {"exp": datetime.utcnow() + timedelta(hours=1)}
        token = jwt.encode(payload, "your-secret-key-here", algorithm="HS256")

        with pytest.raises(ValueError, match="无效的令牌"):
            verify_token(token)

    def test_verify_token_with_non_integer_sub(self):
        """测试：验证 sub 字段非整数的令牌"""
        from services.jwt_service import verify_token

        payload = {
            "sub": "not-a-number",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(payload, "your-secret-key-here", algorithm="HS256")

        # 这会抛出 ValueError 因为 int("not-a-number") 失败
        with pytest.raises(ValueError):
            verify_token(token)


class TestJWTSecretSecurity:
    """JWT 密钥安全性测试"""

    def test_default_secret_is_insecure(self):
        """测试：默认密钥不安全（C3 问题验证）"""
        from config import settings

        # 验证默认密钥是已知的弱密钥
        assert settings.JWT_SECRET == "your-secret-key-here"

        # 这个测试提醒：生产环境必须设置 JWT_SECRET 环境变量

    def test_token_with_default_secret_can_be_forged(self):
        """测试：使用默认密钥可以伪造令牌"""
        from services.jwt_service import create_access_token

        # 使用默认密钥创建令牌
        token = create_access_token(1)

        # 攻击者知道默认密钥，可以解码并重新编码
        payload = jwt.decode(token, "your-secret-key-here", algorithms=["HS256"])

        # 修改用户 ID
        payload["sub"] = "999"  # 攻击者想要冒充的用户

        # 使用相同的密钥重新签名
        forged_token = jwt.encode(payload, "your-secret-key-here", algorithm="HS256")

        # 验证伪造的令牌有效
        from services.jwt_service import verify_token
        result = verify_token(forged_token)
        assert result == 999  # 攻击成功
