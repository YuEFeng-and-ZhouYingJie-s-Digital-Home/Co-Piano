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
    "AppleCallbackRequest",
    "BlockCompleteRequest",
    "BlockCompleteResponse",
    "CurriculumBlock",
    "CurriculumDay",
    "CurriculumWeekResponse",
    "EvaluationCreateRequest",
    "EvaluationCreateResponse",
    "EvaluationListResponse",
    "EvaluationResponse",
    "FeedbackHistoryItem",
    "FeedbackHistoryResponse",
    "FeedbackRequest",
    "FeedbackResponse",
    "GoogleCallbackRequest",
    "LoginRequest",
    "MessageResponse",
    "OAuthAccountInfo",
    "OAuthLinkRequest",
    "RefreshRequest",
    "SightReadingAnswerRequest",
    "SightReadingAnswerResponse",
    "SightReadingQuestion",
    "SightReadingSessionResponse",
    "SightReadingSessionStats",
    "SightReadingStartRequest",
    "SightReadingStartResponse",
    "SignupRequest",
    "TokenResponse",
    "UserResponse",
    "WeChatCallbackRequest",
]
