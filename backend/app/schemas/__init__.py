"""Schemas package"""
from .auth import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from .curriculum import (
    BlockCompleteRequest,
    BlockCompleteResponse,
    CurriculumBlock,
    CurriculumDay,
    CurriculumWeekResponse,
)
from .evaluation import (
    EvaluationCreateRequest,
    EvaluationCreateResponse,
    EvaluationListResponse,
    EvaluationResponse,
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
    "EvaluationCreateRequest",
    "EvaluationCreateResponse",
    "EvaluationResponse",
    "EvaluationListResponse",
    "CurriculumBlock",
    "CurriculumDay",
    "CurriculumWeekResponse",
    "BlockCompleteRequest",
    "BlockCompleteResponse",
]
