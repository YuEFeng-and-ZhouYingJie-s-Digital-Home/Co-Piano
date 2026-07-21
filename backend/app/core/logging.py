"""
结构化日志 (structlog)
========================

JSON 格式输出,方便 Sentry / Loki / CloudWatch 收集
"""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.core.config import settings


def _add_severity(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """加 severity 字段(GCP/Loki 习惯)"""
    level = event_dict.get("level", method_name.upper())
    event_dict["severity"] = level
    return event_dict


def _add_service(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """加 service 字段,方便多服务日志聚合"""
    event_dict["service"] = settings.app_name
    event_dict["version"] = settings.app_version
    event_dict["env"] = settings.env
    # logger 可能是 PrintLogger(没 .name)或 stdlib Logger
    if hasattr(logger, "name"):
        event_dict["logger"] = logger.name
    return event_dict


def setup_logging() -> None:
    """配置 stdlib logging + structlog

    设计:
    - stdlib logging (logging.getLogger) 走普通 stdout 输出
    - structlog (get_logger) 走 JSON/console
    - 两者不互相干扰,各管各的
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # 共享 processors
    # 注意: 不要用 stdlib.add_logger_name(需要 stdlib Logger),
    # 这里 logger 用 PrintLogger,直接 _add_service 加 logger 名字
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        _add_severity,
        _add_service,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # 渲染器: 开发用 console,生产用 JSON
    if settings.is_production:
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())

    # 配置 structlog
    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # 配置 stdlib logging (不影响 structlog,只是接管 uvicorn / sqlalchemy 等的输出)
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
        level=log_level,
        force=True,
    )

    # 降低 uvicorn 默认日志噪音
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


def get_logger(name: str | None = None) -> Any:
    """获取 structlog logger(返回 BoundLogger,支持 .bind / .info / .warning 等)"""
    return structlog.get_logger(name)
