"""Schemas package"""
from .auth import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from .oauth import (
    AppleCallbackRequest,
    GoogleCallbackRequest,
    OAuthAccountInfo,
    OAuthLinkRequest,
    WeChatCallbackRequest,
)

__all__ = [
    "SignupRequest",
    "LoginRequest",
    "RefreshRequest",
    "TokenResponse",
    "UserResponse",
    "MessageResponse",
    "AppleCallbackRequest",
    "GoogleCallbackRequest",
    "WeChatCallbackRequest",
    "OAuthLinkRequest",
    "OAuthAccountInfo",
]
