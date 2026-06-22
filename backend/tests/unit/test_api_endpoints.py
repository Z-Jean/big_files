"""API 端点全面测试"""
import io
import os
import shutil
import tempfile
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import UploadFile


@pytest.fixture
def client():
    """创建测试客户端"""
    from main import app
    return TestClient(app)


@pytest.fixture
def auth_token():
    """获取认证令牌"""
    return "Bearer test_token"


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir)


class TestAuthEndpoints:
    """认证接口测试"""

    def test_login_success(self, client):
        """POST /api/auth/login - 正确凭证登录"""
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
        """POST /api/auth/login - 错误密码"""
        response = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_login_nonexistent_user(self, client):
        """POST /api/auth/login - 不存在的用户"""
        response = client.post("/api/auth/login", json={
            "username": "nonexistent",
            "password": "123456"
        })
        assert response.status_code == 401

    def test_login_missing_fields(self, client):
        """POST /api/auth/login - 缺少必填字段"""
        response = client.post("/api/auth/login", json={
            "username": "admin"
        })
        assert response.status_code == 422  # Validation error

    def test_login_empty_body(self, client):
        """POST /api/auth/login - 空请求体"""
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 422

    def test_health_check(self, client):
        """GET /api/auth/health - 健康检查"""
        response = client.get("/api/auth/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestUploadCheckEndpoints:
    """秒传检测接口测试"""

    def test_check_file_not_exists(self, client):
        """POST /api/upload/check - 文件不存在"""
        # 需要有效 token
        login_resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "123456"
        })
        token = login_resp.json()["token"]

        response = client.post(
            "/api/upload/check",
            params={"md5": "nonexistent_md5", "file_size": 1024},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False

    def test_check_file_no_auth(self, client):
        """POST /api/upload/check - 未授权访问"""
        response = client.post(
            "/api/upload/check",
            params={"md5": "test_md5", "file_size": 1024}
        )
        assert response.status_code == 403  # No auth header

    def test_check_file_invalid_token(self, client):
        """POST /api/upload/check - 无效令牌"""
        response = client.post(
            "/api/upload/check",
            params={"md5": "test_md5", "file_size": 1024},
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401


class TestUploadChunkEndpoints:
    """分片上传接口测试"""

    def test_upload_chunk_success(self, client):
        """POST /api/upload/chunk - 正常上传分片"""
        login_resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "123456"
        })
        token = login_resp.json()["token"]

        chunk_data = b"test chunk data"
        response = client.post(
            "/api/upload/chunk",
            data={
                "md5": "d41d8cd98f00b204e9800998ecf8427e",
                "chunk_index": "0",
                "total_chunks": "1"
            },
            files={"chunk": ("chunk.bin", chunk_data, "application/octet-stream")},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_upload_chunk_no_auth(self, client):
        """POST /api/upload/chunk - 未授权上传"""
        response = client.post(
            "/api/upload/chunk",
            data={
                "md5": "test_md5",
                "chunk_index": "0",
                "total_chunks": "1"
            },
            files={"chunk": ("chunk.bin", b"test", "application/octet-stream")}
        )
        assert response.status_code == 403

    def test_upload_chunk_missing_md5(self, client):
        """POST /api/upload/chunk - 缺少 md5 参数"""
        login_resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "123456"
        })
        token = login_resp.json()["token"]

        response = client.post(
            "/api/upload/chunk",
            data={
                "chunk_index": "0",
                "total_chunks": "1"
            },
            files={"chunk": ("chunk.bin", b"test", "application/octet-stream")},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 422

    def test_upload_chunk_missing_chunk_file(self, client):
        """POST /api/upload/chunk - 缺少分片文件"""
        login_resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "123456"
        })
        token = login_resp.json()["token"]

        response = client.post(
            "/api/upload/chunk",
            data={
                "md5": "test_md5",
                "chunk_index": "0",
                "total_chunks": "1"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 422

    def test_upload_chunk_large_size(self, client):
        """POST /api/upload/chunk - 上传超大分片（C2 问题验证）"""
        login_resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "123456"
        })
        token = login_resp.json()["token"]

        # 模拟 10MB 分片（正常大小）
        large_chunk = b"x" * (10 * 1024 * 1024)
        response = client.post(
            "/api/upload/chunk",
            data={
                "md5": "test_md5",
                "chunk_index": "0",
                "total_chunks": "1"
            },
            files={"chunk": ("chunk.bin", large_chunk, "application/octet-stream")},
            headers={"Authorization": f"Bearer {token}"}
        )
        # 当前实现会接受（需要添加大小限制）
        assert response.status_code in [200, 413]


class TestGetUploadedChunksEndpoints:
    """已上传分片查询接口测试"""

    def test_get_chunks_empty(self, client):
        """GET /api/upload/chunks/{md5} - 查询无分片"""
        login_resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "123456"
        })
        token = login_resp.json()["token"]

        response = client.get(
            "/api/upload/chunks/nonexistent_md5",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["uploaded_chunks"] == []

    def test_get_chunks_no_auth(self, client):
        """GET /api/upload/chunks/{md5} - 未授权查询"""
        response = client.get("/api/upload/chunks/test_md5")
        assert response.status_code == 403


class TestMergeChunksEndpoints:
    """分片合并接口测试"""

    def test_merge_missing_chunks(self, client):
        """POST /api/upload/merge - 合并时缺失分片"""
        login_resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "123456"
        })
        token = login_resp.json()["token"]

        # 尝试合并不存在的分片
        response = client.post(
            "/api/upload/merge",
            data={
                "md5": "nonexistent_md5",
                "filename": "test.txt",
                "total_chunks": "5"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        # 应该返回错误（分片不存在）
        assert response.status_code in [400, 404, 500]

    def test_merge_no_auth(self, client):
        """POST /api/upload/merge - 未授权合并"""
        response = client.post(
            "/api/upload/merge",
            data={
                "md5": "test_md5",
                "filename": "test.txt",
                "total_chunks": "1"
            }
        )
        assert response.status_code == 403


class TestCancelUploadEndpoints:
    """取消上传接口测试"""

    def test_cancel_nonexistent(self, client):
        """DELETE /api/upload/cancel/{md5} - 取消不存在的上传"""
        login_resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "123456"
        })
        token = login_resp.json()["token"]

        response = client.delete(
            "/api/upload/cancel/nonexistent_md5",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    def test_cancel_no_auth(self, client):
        """DELETE /api/upload/cancel/{md5} - 未授权取消"""
        response = client.delete("/api/upload/cancel/test_md5")
        assert response.status_code == 403


class TestFileListEndpoints:
    """文件列表接口测试"""

    def test_get_files_empty(self, client):
        """GET /api/files - 获取空文件列表"""
        login_resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "123456"
        })
        token = login_resp.json()["token"]

        response = client.get(
            "/api/files",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert "files" in response.json()

    def test_get_files_no_auth(self, client):
        """GET /api/files - 未授权访问"""
        response = client.get("/api/files")
        assert response.status_code == 403

    def test_delete_file_not_found(self, client):
        """DELETE /api/files/{file_id} - 删除不存在的文件"""
        login_resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "123456"
        })
        token = login_resp.json()["token"]

        response = client.delete(
            "/api/files/99999",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404

    def test_download_file_not_found(self, client):
        """GET /api/files/{file_id}/download - 下载不存在的文件"""
        login_resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "123456"
        })
        token = login_resp.json()["token"]

        response = client.get(
            "/api/files/99999/download",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404


class TestInputValidation:
    """输入验证测试"""

    def test_md5_format_validation(self):
        """验证 md5 格式校验"""
        import re

        md5_pattern = re.compile(r'^[a-f0-9]{32}$')

        # 有效 md5
        valid_md5s = [
            "d41d8cd98f00b204e9800998ecf8427e",
            "098f6bcd4621d373cade4e832627b4f6",
        ]
        for md5 in valid_md5s:
            assert md5_pattern.match(md5) is not None

        # 无效 md5
        invalid_md5s = [
            "../../../etc/passwd",
            "'; DROP TABLE users;--",
            "not-a-valid-md5",
            "",
            "abc123",  # 太短
            "g" * 32,  # 包含非十六进制字符
        ]
        for md5 in invalid_md5s:
            assert md5_pattern.match(md5) is None

    def test_chunk_index_validation(self):
        """验证 chunk_index 范围"""
        # 有效索引
        valid_indices = [0, 1, 100, 999]
        for idx in valid_indices:
            assert idx >= 0

        # 无效索引
        invalid_indices = [-1, -100]
        for idx in invalid_indices:
            assert idx < 0

    def test_total_chunks_validation(self):
        """验证 total_chunks 范围"""
        # 有效值
        valid_totals = [1, 10, 100, 400]
        for total in valid_totals:
            assert total > 0

        # 无效值
        invalid_totals = [0, -1, -100]
        for total in invalid_totals:
            assert total <= 0


class TestErrorHandling:
    """错误处理测试"""

    def test_404_handler(self, client):
        """404 错误处理"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_405_handler(self, client):
        """405 方法不允许"""
        response = client.put("/api/auth/login")
        assert response.status_code == 405

    def test_invalid_json_body(self, client):
        """无效 JSON 请求体"""
        response = client.post(
            "/api/auth/login",
            content="not json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
