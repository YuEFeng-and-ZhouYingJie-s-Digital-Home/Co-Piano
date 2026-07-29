"""
S3/MinIO 存储服务
==================

封装 boto3,提供:
- upload_file(local_path, key) → S3 URL
- upload_bytes(data, key, content_type) → S3 URL
- get_presigned_url(key, expires=3600) → 临时访问 URL
- delete_file(key) → bool
- exists(key) → bool
- get_bytes(key) → bytes

支持 MinIO (本地开发) + AWS S3 (生产),配置走 .env
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger("copiano.storage")


class StorageService:
    """S3/MinIO 存储服务"""

    def __init__(self) -> None:
        self._client = None
        self.bucket = settings.s3_bucket or "copiano-midi"

    @property
    def client(self):
        """懒加载 boto3 客户端"""
        if self._client is None:
            # MinIO 兼容 S3 API,只需 endpoint_url + signature_version=s3v4
            kwargs = {
                "service_name": "s3",
                "region_name": settings.s3_region or "us-east-1",
                "aws_access_key_id": settings.s3_access_key or "copiano",
                "aws_secret_access_key": settings.s3_secret_key or "mNioCopiano2026Secret",
                "config": Config(
                    signature_version="s3v4",
                    s3={"addressing_style": "path"} if settings.s3_endpoint_url else {},
                ),
            }
            if settings.s3_endpoint_url:
                kwargs["endpoint_url"] = settings.s3_endpoint_url
            self._client = boto3.client(**kwargs)
        return self._client

    def _ensure_bucket(self) -> None:
        """确保 bucket 存在,不存在则创建"""
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("404", "NoSuchBucket", "NotFound"):
                logger.info("creating_bucket: %s", self.bucket)
                self.client.create_bucket(Bucket=self.bucket)
            else:
                raise

    def _build_key(self, prefix: str, filename: str) -> str:
        """构造对象 key

        路径格式: <prefix>/<YYYY>/<MM>/<uuid>_<safe_filename>
        """
        now = datetime.utcnow()
        # 防路径穿越
        safe_name = Path(filename).name.replace("..", "").replace("/", "_")
        unique = uuid.uuid4().hex[:12]
        return f"{prefix}/{now.year}/{now.month:02d}/{unique}_{safe_name}"

    def upload_file(
        self,
        local_path: str | Path,
        prefix: str = "midi",
        content_type: str = "audio/midi",
        public: bool = False,
    ) -> str:
        """上传本地文件 → S3 key"""
        self._ensure_bucket()
        key = self._build_key(prefix, str(local_path))
        self.client.upload_file(
            str(local_path),
            self.bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        logger.info("uploaded s3://%s/%s (%s)", self.bucket, key, content_type)
        return f"s3://{self.bucket}/{key}"

    def upload_bytes(
        self,
        data: bytes,
        key_suffix: str = "data.bin",
        prefix: str = "midi",
        content_type: str = "application/octet-stream",
        public: bool = False,
    ) -> str:
        """上传 bytes → S3 key"""
        self._ensure_bucket()
        key = self._build_key(prefix, key_suffix)
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        logger.info("uploaded s3://%s/%s (%d bytes)", self.bucket, key, len(data))
        return f"s3://{self.bucket}/{key}"

    def get_presigned_url(
        self,
        s3_uri: str,
        expires_seconds: int = 3600,
        method: str = "get_object",
    ) -> str:
        """生成 presigned URL(默认 1 小时有效)

        s3_uri: "s3://bucket/key" 或 "key"
        """
        bucket, key = self._parse_uri(s3_uri)
        url = self.client.generate_presigned_url(
            ClientMethod=method,
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )
        return url

    def get_public_url(self, s3_uri: str) -> str:
        """生成公开访问 URL(假设 bucket 有 public-read 策略)

        对 MinIO 本地开发,s3_endpoint_url + bucket + key 拼成 URL
        对 AWS S3,CloudFront 域名或 bucket website
        """
        bucket, key = self._parse_uri(s3_uri)
        # 优先用 public URL(给客户端用)
        base = settings.s3_public_url or settings.s3_endpoint_url
        if base:
            return f"{base.rstrip('/')}/{bucket}/{key}"
        # AWS S3 默认
        return f"https://{bucket}.s3.{settings.s3_region}.amazonaws.com/{key}"

    def delete_file(self, s3_uri: str) -> bool:
        """删除对象"""
        try:
            bucket, key = self._parse_uri(s3_uri)
            self.client.delete_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            logger.warning("delete_failed: %s (%s)", s3_uri, e)
            return False

    def exists(self, s3_uri: str) -> bool:
        """检查对象是否存在"""
        try:
            bucket, key = self._parse_uri(s3_uri)
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False

    def get_bytes(self, s3_uri: str) -> bytes:
        """下载对象 → bytes"""
        bucket, key = self._parse_uri(s3_uri)
        response = self.client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()

    def _parse_uri(self, s3_uri: str) -> tuple[str, str]:
        """解析 s3://bucket/key → (bucket, key)"""
        s3_uri = s3_uri.removeprefix("s3://")
        parts = s3_uri.split("/", 1)
        bucket = parts[0] if parts else self.bucket
        key = parts[1] if len(parts) > 1 else ""
        return bucket, key


# Singleton
storage_service = StorageService()
