"""
Redis 缓存服务
================

封装 redis-py,提供:
- get(key) → dict | None
- set(key, value, ttl_seconds) → bool
- delete(key) → bool
- exists(key) → bool
- incr(key, ttl=...) → int
- 字典/JSON 自动序列化

懒加载连接,Redis 不可用时降级到 no-op(不抛异常)
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import redis

from app.core.config import settings

logger = logging.getLogger("copiano.cache")


class CacheService:
    """Redis 缓存服务(失败降级,无脑 None)"""

    def __init__(self) -> None:
        self._client: redis.Redis | None = None
        self._enabled = True

    @property
    def client(self) -> redis.Redis | None:
        """懒加载 Redis 客户端"""
        if not self._enabled:
            return None
        if self._client is None:
            try:
                self._client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                # ping 一下确认连通
                self._client.ping()
                logger.info("cache_connected: %s", settings.redis_url)
            except (redis.ConnectionError, redis.TimeoutError) as e:
                logger.warning("cache_unavailable: %s", e)
                self._client = None
                self._enabled = False  # 不再重试
        return self._client

    def is_available(self) -> bool:
        """Redis 是否可用"""
        return self.client is not None

    # ──────────────────────────────────────────────
    # 基础操作
    # ──────────────────────────────────────────────
    def get(self, key: str) -> dict | None:
        """获取 JSON 缓存(自动反序列化)"""
        client = self.client
        if not client:
            return None
        try:
            raw = client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.warning("cache_get_failed: %s key=%s", e, key)
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 86400,
    ) -> bool:
        """设置 JSON 缓存(自动序列化 + TTL)"""
        client = self.client
        if not client:
            return False
        try:
            payload = json.dumps(value, default=str)
            client.set(key, payload, ex=ttl_seconds)
            return True
        except (redis.RedisError, TypeError) as e:
            logger.warning("cache_set_failed: %s key=%s", e, key)
            return False

    def delete(self, key: str) -> bool:
        client = self.client
        if not client:
            return False
        try:
            client.delete(key)
            return True
        except redis.RedisError as e:
            logger.warning("cache_delete_failed: %s", e)
            return False

    def exists(self, key: str) -> bool:
        client = self.client
        if not client:
            return False
        try:
            return bool(client.exists(key))
        except redis.RedisError:
            return False

    def incr(self, key: str, ttl_seconds: int | None = None) -> int:
        """原子递增(限流场景)"""
        client = self.client
        if not client:
            return 0
        try:
            n = client.incr(key)
            if ttl_seconds and n == 1:  # 第一次设 TTL
                client.expire(key, ttl_seconds)
            return int(n)
        except redis.RedisError as e:
            logger.warning("cache_incr_failed: %s", e)
            return 0

    def ttl(self, key: str) -> int:
        """查询剩余 TTL(秒)"""
        client = self.client
        if not client:
            return -2
        try:
            return int(client.ttl(key))
        except redis.RedisError:
            return -2

    # ──────────────────────────────────────────────
    # 业务级辅助
    # ──────────────────────────────────────────────
    @staticmethod
    def midi_hash(midi_path: str | Path, period_hint: str = "") -> str:
        """MIDI 文件内容 hash + period_hint → 缓存 key 后缀

        同样内容同样 period → 同样 key,命中缓存
        """
        path = Path(midi_path)
        if not path.exists():
            return hashlib.md5(f"missing:{midi_path}".encode()).hexdigest()[:16]
        # 读 MIDI 头 + 元信息(不全读,大数据 MIDI 节省 IO)
        with open(path, "rb") as f:
            head = f.read(8192)
        size = path.stat().st_size
        mtime = int(path.stat().st_mtime)
        raw = head + size.to_bytes(8, "little") + mtime.to_bytes(8, "little") + period_hint.encode()
        return hashlib.md5(raw).hexdigest()[:16]

    @classmethod
    def eval_key(cls, midi_path: str | Path, period_hint: str = "") -> str:
        """评估结果缓存 key"""
        h = cls.midi_hash(midi_path, period_hint)
        return f"eval:{h}"


# Singleton
cache_service = CacheService()
