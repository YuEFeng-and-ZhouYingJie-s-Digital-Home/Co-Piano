"""
应用配置 — Pydantic Settings
=============================

从环境变量加载,支持 .env 文件
"""
import secrets
from functools import lru_cache

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
    # 正则匹配 — 适合 Cloudflare Tunnel 随机 URL / 未来多子域
    # 例: ^https://.*\\.trycloudflare\\.com$ 匹配所有 trycloudflare 域名
    cors_origin_regex: str = Field(
        default="",
        description="CORS allow_origin_regex (逗号分隔,多个 pattern 任一匹配即允许)",
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

    # ── OAuth ──
    apple_client_id: str = ""  # Bundle ID or Service ID
    google_client_id: str = ""  # OAuth 2.0 Client ID
    wechat_app_id: str = ""
    wechat_app_secret: str = ""

    # ── S3 / MinIO ──
    s3_endpoint_url: str = "http://127.0.0.1:9000"  # FastAPI → MinIO 内部
    s3_public_url: str = ""  # 客户端访问的公网 URL(空则用 s3_endpoint_url)
    s3_bucket: str = "copiano-midi"
    s3_access_key: str = "copiano"
    s3_secret_key: str = "mNioCopiano2026Secret"
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
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def cors_origin_regex_list(self) -> list[str]:
        """
        解析 CORS_ORIGIN_REGEX 为正则 pattern 列表 (FastAPI/Starlette 接受 list)
        例: '^https://.*\\.trycloudflare\\.com$,^http://localhost:[0-9]+$'
        """
        return [p.strip() for p in self.cors_origin_regex.split(",") if p.strip()]

    def cors_origin_regex_combined(self) -> str | None:
        """
        把多个 pattern 合并成一个 (用 | 连接),如果只有一个就直接返回
        FastAPI 的 allow_origin_regex 只接受单字符串
        """
        patterns = self.cors_origin_regex_list
        if not patterns:
            return None
        if len(patterns) == 1:
            return patterns[0]
        return "|".join(f"(?:{p})" for p in patterns)

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """全局单例"""
    return Settings()


settings = get_settings()
