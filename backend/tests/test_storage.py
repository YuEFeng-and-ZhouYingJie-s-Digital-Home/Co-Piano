"""
Storage service tests (S3/MinIO wrapper)
=========================================

用 moto 模拟 S3,无需真实 MinIO
"""
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import boto3
import pytest
from moto import mock_aws

from app.services.storage import StorageService, storage_service


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────
@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for moto"""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def s3_mock(aws_credentials):
    """Mock S3 + 创建测试 bucket(用 AWS endpoint 而非 MinIO)"""
    # 临时把 settings.s3_endpoint_url 清空,让 boto3 用 AWS 默认
    from app.core import config as config_module
    original_endpoint = config_module.settings.s3_endpoint_url
    original_public = config_module.settings.s3_public_url
    config_module.settings.s3_endpoint_url = ""
    config_module.settings.s3_public_url = ""
    try:
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket="copiano-midi")
            yield client
    finally:
        config_module.settings.s3_endpoint_url = original_endpoint
        config_module.settings.s3_public_url = original_public


# ──────────────────────────────────────────────
# Unit tests
# ──────────────────────────────────────────────
def test_storage_service_init():
    """StorageService 可实例化"""
    s = StorageService()
    assert s.bucket == "copiano-midi"


def test_parse_uri_with_scheme():
    """解析 s3://bucket/key"""
    s = StorageService()
    bucket, key = s._parse_uri("s3://my-bucket/path/to/file.mid")
    assert bucket == "my-bucket"
    assert key == "path/to/file.mid"


def test_parse_uri_without_scheme():
    """解析不带 scheme 的 path/to/file.mid

    行为:split('/', 1) 把 'path/to/file.mid' 拆成 ['path', 'to/file.mid']
    所以 bucket='path', key='to/file.mid'
    """
    s = StorageService()
    bucket, key = s._parse_uri("path/to/file.mid")
    assert bucket == "path"
    assert key == "to/file.mid"


def test_build_key():
    """key 格式: <prefix>/<YYYY>/<MM>/<uuid>_<filename>"""
    s = StorageService()
    key = s._build_key("midi", "test.mid")
    parts = key.split("/")
    assert parts[0] == "midi"
    assert len(parts) == 4  # midi/2026/07/uuid_test.mid
    assert parts[1].isdigit() and len(parts[1]) == 4
    assert parts[2].isdigit() and len(parts[2]) == 2
    assert parts[3].endswith("test.mid")


def test_build_key_sanitizes_path_traversal():
    """防止 .. 路径穿越"""
    s = StorageService()
    key = s._build_key("midi", "../../etc/passwd")
    assert ".." not in key
    assert "/" not in Path(key).name.replace("..", "")  # 路径已被替换


# ──────────────────────────────────────────────
# 集成测试 (moto mock S3)
# ──────────────────────────────────────────────
def test_upload_bytes(s3_mock):
    """upload_bytes 写入 S3"""
    s = StorageService()
    data = b"fake midi content"
    uri = s.upload_bytes(data, "test.mid", prefix="test")
    assert uri.startswith("s3://copiano-midi/test/")

    # 验证可读回
    response = s3_mock.get_object(Bucket="copiano-midi", Key=uri.split("/", 3)[3])
    assert response["Body"].read() == data


def test_upload_file(s3_mock, tmp_path):
    """upload_file 从本地路径上传"""
    s = StorageService()
    test_file = tmp_path / "test.mid"
    test_file.write_bytes(b"local midi content")

    uri = s.upload_file(test_file, prefix="uploads")
    assert uri.startswith("s3://copiano-midi/uploads/")

    # 验证内容
    response = s3_mock.get_object(Bucket="copiano-midi", Key=uri.split("/", 3)[3])
    assert response["Body"].read() == b"local midi content"
    assert response["ContentType"] == "audio/midi"


def test_get_presigned_url(s3_mock):
    """get_presigned_url 生成临时 URL"""
    s = StorageService()
    uri = s.upload_bytes(b"data", "x.mid", prefix="presign")
    url = s.get_presigned_url(uri, expires_seconds=300)
    assert url.startswith("https://") or url.startswith("http://")
    assert "X-Amz-Signature" in url or "Signature" in url
    assert "X-Amz-Expires=300" in url


def test_delete_file(s3_mock):
    """delete_file 删除对象"""
    s = StorageService()
    uri = s.upload_bytes(b"to delete", "x.mid", prefix="delete")
    assert s.exists(uri)

    assert s.delete_file(uri) is True
    assert s.exists(uri) is False


def test_exists(s3_mock):
    """exists 检查对象存在"""
    s = StorageService()
    uri = s.upload_bytes(b"x", "x.mid", prefix="exists")
    assert s.exists(uri) is True
    assert s.exists("s3://copiano-midi/nonexistent.mid") is False


def test_get_bytes(s3_mock):
    """get_bytes 下载对象"""
    s = StorageService()
    data = b"download me"
    uri = s.upload_bytes(data, "x.mid", prefix="download")
    downloaded = s.get_bytes(uri)
    assert downloaded == data


def test_upload_bytes_custom_content_type(s3_mock):
    """upload_bytes 支持自定义 content_type"""
    s = StorageService()
    uri = s.upload_bytes(b"json", "x.json", prefix="ct", content_type="application/json")
    key = uri.split("/", 3)[3]
    response = s3_mock.get_object(Bucket="copiano-midi", Key=key)
    assert response["ContentType"] == "application/json"


def test_ensure_bucket_idempotent(s3_mock):
    """_ensure_bucket 重复调用不报错"""
    s = StorageService()
    s._ensure_bucket()
    s._ensure_bucket()  # 第二次应直接通过(head_bucket 200)
    # 列出 buckets 验证
    response = s3_mock.list_buckets()
    bucket_names = [b["Name"] for b in response["Buckets"]]
    assert "copiano-midi" in bucket_names


# ──────────────────────────────────────────────
# Singleton
# ──────────────────────────────────────────────
def test_storage_service_singleton():
    """storage_service 是单例"""
    from app.services.storage import storage_service as ss2
    assert storage_service is ss2


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(["pytest", __file__, "-v", "--tb=short"], cwd=str(BACKEND_DIR))
    sys.exit(result.returncode)
