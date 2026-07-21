"""
User 模型
=========

字段:
- id (UUID)
- email (unique)
- password_hash (bcrypt)
- name
- age (用于银发模式自动激活 ≥60)
- is_senior (显式 override)
- subscription_tier (free / pro / senior / teacher / school)
- preferred_language (zh-CN / en-US)
- oauth_provider + oauth_id (Apple/Google/微信)
- last_login_at
- is_active / is_verified (邮箱验证)
"""
import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.evaluation import Evaluation
    from app.models.curriculum import CurriculumProgress
    from app.models.sight_reading import SightReadingSession


class SubscriptionTier(str, enum.Enum):
    """订阅档位"""
    FREE = "free"           # 3 evals/mo
    PRO = "pro"             # ¥29/mo
    SENIOR = "senior"       # 免费 (60+ 自动)
    TEACHER = "teacher"     # ¥99/mo
    SCHOOL = "school"       # ¥999/mo


class OAuthProvider(str, enum.Enum):
    """OAuth 提供方"""
    APPLE = "apple"
    GOOGLE = "google"
    WECHAT = "wechat"
    LOCAL = "local"  # email/password


class User(Base, TimestampMixin):
    __tablename__ = "users"

    # 主键
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # 凭据
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,  # OAuth 用户可无密码
    )

    # 资料
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preferred_language: Mapped[str] = mapped_column(
        String(10),
        default="zh-CN",
        nullable=False,
    )

    # 银发模式 (age ≥ 60 自动激活,可显式 override)
    is_senior: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 订阅
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, name="subscription_tier_enum"),
        default=SubscriptionTier.FREE,
        nullable=False,
        index=True,
    )

    # OAuth
    oauth_provider: Mapped[OAuthProvider] = mapped_column(
        Enum(OAuthProvider, name="oauth_provider_enum"),
        default=OAuthProvider.LOCAL,
        nullable=False,
    )
    oauth_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 关系
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    curriculum_progress: Mapped[list["CurriculumProgress"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    sight_reading_sessions: Mapped[list["SightReadingSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ──────────────────────────────────────────────
    # 业务方法
    # ──────────────────────────────────────────────
    def should_auto_senior(self) -> bool:
        """银发模式自动激活条件:age >= 60"""
        if self.is_senior:
            return True
        if self.age is not None and self.age >= 60:
            return True
        return False

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.subscription_tier.value})>"
