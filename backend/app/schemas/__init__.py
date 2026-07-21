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
from .feedback import (
    FeedbackHistoryItem,
    FeedbackHistoryResponse,
    FeedbackRequest,
    FeedbackResponse,
)
from .oauth import (
    AppleCallbackRequest,
    GoogleCallbackRequest,
    OAuthAccountInfo,
    OAuthLinkRequest,
    WeChatCallbackRequest,
)
from .sight_reading import (
    SightReadingAnswerRequest,
    SightReadingAnswerResponse,
    SightReadingQuestion,
    SightReadingSessionResponse,
    SightReadingSessionStats,
    SightReadingStartRequest,
    SightReadingStartResponse,
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
    "SightReadingStartRequest",
    "SightReadingStartResponse",
    "SightReadingQuestion",
    "SightReadingAnswerRequest",
    "SightReadingAnswerResponse",
    "SightReadingSessionResponse",
    "SightReadingSessionStats",
    "FeedbackRequest",
    "FeedbackResponse",
    "FeedbackHistoryItem",
    "FeedbackHistoryResponse",
]
