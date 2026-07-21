"""
User Service — 业务逻辑层
==========================
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import OAuthProvider, User


class UserService:
    """用户业务逻辑"""

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        email: str,
        password: str,
        name: Optional[str] = None,
        age: Optional[int] = None,
    ) -> User:
        """注册新用户"""
        # 检查邮箱已存在
        existing = await UserService.get_by_email(db, email)
        if existing:
            raise ValueError(f"Email already registered: {email}")

        user = User(
            email=email.lower(),
            password_hash=hash_password(password),
            name=name,
            age=age,
        )
        # 银发模式自动激活
        if user.should_auto_senior():
            user.is_senior = True

        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate(db: AsyncSession, email: str, password: str) -> Optional[User]:
        """验证邮箱+密码,成功返回 User,失败 None"""
        user = await UserService.get_by_email(db, email)
        if not user:
            return None
        if not user.password_hash:
            return None  # OAuth 用户无密码
        if not verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None

        # 更新最后登录时间
        user.last_login_at = datetime.now(timezone.utc)
        await db.commit()
        return user

    @staticmethod
    async def update_last_login(db: AsyncSession, user: User) -> None:
        user.last_login_at = datetime.now(timezone.utc)
        await db.commit()
