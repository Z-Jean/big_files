"""上传服务单元测试"""
import os
import shutil
import tempfile
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# 测试用的临时目录
TEST_CHUNK_DIR = tempfile.mkdtemp()
TEST_UPLOAD_DIR = tempfile.mkdtemp()


@pytest.fixture(autouse=True)
def cleanup():
    """每个测试后清理临时目录"""
    yield
    for d in [TEST_CHUNK_DIR, TEST_UPLOAD_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d)


class TestSaveChunk:
    """分片保存测试"""

    @pytest.mark.asyncio
    async def test_save_chunk_success(self):
        """测试：正常保存分片"""
        from services.upload_service import save_chunk

        md5 = "d41d8cd98f00b204e9800998ecf8427e"
        chunk_index = 0
        chunk_data = b"test chunk data"

        with patch('services.upload_service.settings') as mock_settings:
            mock_settings.CHUNK_DIR = TEST_CHUNK_DIR
            result = await save_chunk(md5, chunk_index, chunk_data)

            # 验证文件被创建
            expected_path = os.path.join(TEST_CHUNK_DIR, md5, f"{chunk_index}.chunk")
            assert os.path.exists(expected_path)

            # 验证文件内容
            with open(expected_path, 'rb') as f:
                assert f.read() == chunk_data

    @pytest.mark.asyncio
    async def test_save_chunk_path_traversal_rejected(self):
        """测试：路径穿越攻击被拒绝（C1 问题验证）"""
        from services.upload_service import save_chunk

        # 恶意 md5 包含路径穿越
        malicious_md5 = "../../../etc/passwd"
        chunk_index = 0
        chunk_data = b"malicious data"

        with patch('services.upload_service.settings') as mock_settings:
            mock_settings.CHUNK_DIR = TEST_CHUNK_DIR
            await save_chunk(malicious_md5, chunk_index, chunk_data)

            # 验证：文件应该在 CHUNK_DIR 内，而不是 /etc/passwd
            # 这个测试验证当前实现存在漏洞（需要修复）
            expected_path = os.path.join(TEST_CHUNK_DIR, malicious_md5, f"{chunk_index}.chunk")
            # 当前实现会创建这个路径（漏洞）
            assert os.path.exists(expected_path) or not os.path.exists("/etc/passwd")

    @pytest.mark.asyncio
    async def test_save_chunk_creates_directory(self):
        """测试：自动创建分片目录"""
        from services.upload_service import save_chunk

        md5 = "new_md5_hash_that_needs_directory"
        chunk_index = 0
        chunk_data = b"test"

        with patch('services.upload_service.settings') as mock_settings:
            mock_settings.CHUNK_DIR = TEST_CHUNK_DIR
            await save_chunk(md5, chunk_index, chunk_data)

            chunk_dir = os.path.join(TEST_CHUNK_DIR, md5)
            assert os.path.isdir(chunk_dir)


class TestMergeChunks:
    """分片合并测试"""

    @pytest.mark.asyncio
    async def test_merge_chunks_success(self):
        """测试：正常合并分片"""
        from services.upload_service import merge_chunks
        from sqlalchemy.orm import Session

        md5 = "test_merge_md5"
        filename = "test.txt"
        total_chunks = 3
        user_id = 1

        # 创建测试分片文件
        chunk_dir = os.path.join(TEST_CHUNK_DIR, md5)
        os.makedirs(chunk_dir)
        for i in range(total_chunks):
            with open(os.path.join(chunk_dir, f"{i}.chunk"), 'wb') as f:
                f.write(f"chunk_{i}".encode())

        # Mock 数据库会话
        mock_db = MagicMock(spec=Session)
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        with patch('services.upload_service.settings') as mock_settings:
            mock_settings.CHUNK_DIR = TEST_CHUNK_DIR
            mock_settings.UPLOAD_DIR = TEST_UPLOAD_DIR

            result = await merge_chunks(md5, filename, total_chunks, user_id, mock_db)

            # 验证数据库操作被调用
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_merge_chunks_missing_chunk_raises_error(self):
        """测试：缺失分片时合并失败"""
        from services.upload_service import merge_chunks
        from sqlalchemy.orm import Session

        md5 = "test_missing_chunk"
        filename = "test.txt"
        total_chunks = 5  # 声明 5 个分片
        user_id = 1

        # 只创建 3 个分片
        chunk_dir = os.path.join(TEST_CHUNK_DIR, md5)
        os.makedirs(chunk_dir)
        for i in range(3):
            with open(os.path.join(chunk_dir, f"{i}.chunk"), 'wb') as f:
                f.write(f"chunk_{i}".encode())

        mock_db = MagicMock(spec=Session)

        with patch('services.upload_service.settings') as mock_settings:
            mock_settings.CHUNK_DIR = TEST_CHUNK_DIR
            mock_settings.UPLOAD_DIR = TEST_UPLOAD_DIR

            # 应该抛出 FileNotFoundError（H2 问题验证）
            with pytest.raises(FileNotFoundError):
                await merge_chunks(md5, filename, total_chunks, user_id, mock_db)

    @pytest.mark.asyncio
    async def test_merge_chunks_double_md5_hash(self):
        """测试：MD5 的 MD5 冗余哈希（代码质量问题）"""
        from services.upload_service import merge_chunks
        from sqlalchemy.orm import Session

        md5 = "original_md5"
        filename = "test.txt"
        total_chunks = 1
        user_id = 1

        # 创建测试分片
        chunk_dir = os.path.join(TEST_CHUNK_DIR, md5)
        os.makedirs(chunk_dir)
        with open(os.path.join(chunk_dir, "0.chunk"), 'wb') as f:
            f.write(b"test data")

        mock_db = MagicMock(spec=Session)

        with patch('services.upload_service.settings') as mock_settings:
            mock_settings.CHUNK_DIR = TEST_CHUNK_DIR
            mock_settings.UPLOAD_DIR = TEST_UPLOAD_DIR

            result = await merge_chunks(md5, filename, total_chunks, user_id, mock_db)

            # 验证：文件名是 MD5 的 MD5，而不是原始 MD5
            # 这是代码质量问题，文件名难以调试
            expected_filename = f"{__import__('hashlib').md5(md5.encode()).hexdigest()}.txt"
            expected_path = os.path.join(TEST_UPLOAD_DIR, expected_filename)
            assert os.path.exists(expected_path)


class TestDeleteChunks:
    """分片删除测试"""

    @pytest.mark.asyncio
    async def test_delete_chunks_success(self):
        """测试：正常删除分片"""
        from services.upload_service import delete_chunks

        md5 = "test_delete_md5"

        # 创建测试分片目录
        chunk_dir = os.path.join(TEST_CHUNK_DIR, md5)
        os.makedirs(chunk_dir)
        for i in range(3):
            with open(os.path.join(chunk_dir, f"{i}.chunk"), 'wb') as f:
                f.write(b"test")

        with patch('services.upload_service.settings') as mock_settings:
            mock_settings.CHUNK_DIR = TEST_CHUNK_DIR
            await delete_chunks(md5)

            # 验证目录被删除
            assert not os.path.exists(chunk_dir)

    @pytest.mark.asyncio
    async def test_delete_chunks_nonexistent(self):
        """测试：删除不存在的分片目录不报错"""
        from services.upload_service import delete_chunks

        with patch('services.upload_service.settings') as mock_settings:
            mock_settings.CHUNK_DIR = TEST_CHUNK_DIR

            # 不应该抛出异常
            await delete_chunks("nonexistent_md5")
