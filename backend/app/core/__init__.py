"""Core package"""
from .config import Settings, get_settings, settings
from .logging import get_logger, setup_logging
from .rate_limit import (
    RATE_LIMIT_AUTH,
    RATE_LIMIT_DEFAULT,
    RATE_LIMIT_FEEDBACK,
    RATE_LIMIT_UPLOAD,
    RateLimitExceeded,
    get_auth_key,
    get_client_ip,
    limiter,
)
from .security import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)

__all__ = [
    # config
    "Settings",
    "get_settings",
    "settings",
    # security
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "create_token_pair",
    "decode_token",
    # logging
    "get_logger",
    "setup_logging",
    # rate limit
    "limiter",
    "RateLimitExceeded",
    "get_client_ip",
    "get_auth_key",
    "RATE_LIMIT_DEFAULT",
    "RATE_LIMIT_AUTH",
    "RATE_LIMIT_FEEDBACK",
    "RATE_LIMIT_UPLOAD",
]
