"""
CoPiano Database — Base + Engine + Session
==========================================

SQLAlchemy 2.0 风格 (Mapped / mapped_column)
- 单一 Base 类供所有模型继承
- 异步 engine (asyncpg) + 同步 engine (psycopg2) 双轨
- get_db() 依赖函数供 FastAPI 使用
- engine 懒加载,避免 import 时连不上 DB 就崩

作者: CoPiano Team
版本: v4.0 (Phase 7A W2 — A2.2)
"""
import os
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ──────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://copiano:copiano@localhost:5432/copiano",
)
DATABASE_URL_SYNC = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql://copiano:copiano@localhost:5432/copiano",
)


# ──────────────────────────────────────────────
# Base 类
# ──────────────────────────────────────────────
class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""


# ──────────────────────────────────────────────
# Engine 工厂 (懒加载)
# ──────────────────────────────────────────────
_async_engine: AsyncEngine | None = None
_sync_engine: Engine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None
_sync_session_factory: sessionmaker[Session] | None = None


def get_async_engine() -> AsyncEngine:
    """懒加载异步 engine (生产用 asyncpg)"""
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(
            DATABASE_URL,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
            pool_pre_ping=True,
        )
    return _async_engine


def get_sync_engine() -> Engine:
    """懒加载同步 engine (Alembic 迁移用)"""
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(
            DATABASE_URL_SYNC,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            pool_pre_ping=True,
        )
    return _sync_engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """懒加载异步 session factory"""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _async_session_factory


def get_sync_session_factory() -> sessionmaker[Session]:
    """懒加载同步 session factory"""
    global _sync_session_factory
    if _sync_session_factory is None:
        _sync_session_factory = sessionmaker(
            bind=get_sync_engine(),
            class_=Session,
            expire_on_commit=False,
            autoflush=False,
        )
    return _sync_session_factory


# ──────────────────────────────────────────────
# FastAPI 依赖
# ──────────────────────────────────────────────
async def get_async_db() -> Generator[AsyncSession, None, None]:
    """FastAPI 异步依赖"""
    factory = get_async_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI 同步依赖 (用于 sync 路由)"""
    factory = get_sync_session_factory()
    db = factory()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ──────────────────────────────────────────────
# 健康检查
# ──────────────────────────────────────────────
def check_db_connection() -> bool:
    """同步检查 DB 是否可达"""
    try:
        with get_sync_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
