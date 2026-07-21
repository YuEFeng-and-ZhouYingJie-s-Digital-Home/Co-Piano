"""
应用配置 — Pydantic Settings
=============================

从环境变量加载,支持 .env 文件
"""
import secrets
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置"""

    # ── 应用 ──
    app_name: str = "CoPiano API"
    app_version: str = "4.0.0-alpha"
    env: str = Field(default="development", description="development / staging / production")
    debug: bool = Field(default=True)
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    # ── CORS ──
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173,https://copiano.com,https://app.copiano.com"
    )

    # ── JWT ──
    jwt_secret: str = Field(
        default="dev-secret-change-me-in-production-" + secrets.token_urlsafe(32),
        description="JWT 签名密钥(生产必须用 64+ 字符随机)",
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    jwt_issuer: str = "copiano-api"

    # ── Bcrypt ──
    bcrypt_rounds: int = 12

    # ── 数据库 ──
    database_url: str = "postgresql+asyncpg://copiano:copiano@localhost:5432/copiano"
    database_url_sync: str = "postgresql://copiano:copiano@localhost:5432/copiano"

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"

    # ── LLM ──
    qwen_api_url: str = "http://localhost:8080"
    openai_api_key: str = ""

    # ── S3 / MinIO ──
    s3_endpoint_url: str = ""
    s3_bucket: str = "copiano-midi"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"

    # ── 监控 ──
    sentry_dsn: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """全局单例"""
    return Settings()


settings = get_settings()
