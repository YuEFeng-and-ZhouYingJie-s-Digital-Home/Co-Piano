"""
Cache service tests (Redis wrapper)
====================================

用 fakeredis 模拟,无需真实 Redis
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import json
import pytest

from app.services.cache import CacheService, cache_service


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────
@pytest.fixture
def fake_redis(monkeypatch):
    """用 fakeredis 替换 CacheService.client"""
    import fakeredis
    fr = fakeredis.FakeRedis(decode_responses=True)

    # monkey-patch 整个 client property,让所有 instance 都用 fakeredis
    def _fake_client(self):
        return fr

    monkeypatch.setattr(CacheService, "client", property(_fake_client))
    monkeypatch.setattr(CacheService, "is_available", lambda self: True)

    yield fr
    fr.flushall()


# ──────────────────────────────────────────────
# Unit tests
# ──────────────────────────────────────────────
def test_cache_service_init():
    """CacheService 可实例化"""
    s = CacheService()
    assert s is not None


def test_is_available_when_redis_unreachable(monkeypatch):
    """Redis 不可达时 is_available() = False"""
    # 清空 client + enabled 强制重新检测
    CacheService._client = None
    CacheService._enabled = True
    # Patch 临时 settings
    from app.core import config as cm
    monkeypatch.setattr(cm.settings, "redis_url", "redis://nonexistent-host:65535")
    s = CacheService()
    # 不应抛异常,返回 None
    assert s.client is None
    assert s.is_available() is False
    # 第二次访问直接降级(不再尝试连接)
    assert s.client is None


def test_get_set_basic(fake_redis):
    """基础 get/set 往返"""
    s = CacheService()
    assert s.set("test:key", {"foo": "bar", "n": 42}, ttl_seconds=60) is True
    result = s.get("test:key")
    assert result == {"foo": "bar", "n": 42}


def test_get_missing(fake_redis):
    """不存在的 key → None"""
    s = CacheService()
    assert s.get("nope") is None


def test_set_ttl(fake_redis):
    """TTL 设置正确"""
    s = CacheService()
    s.set("ttl:key", "value", ttl_seconds=60)
    ttl = s.ttl("ttl:key")
    # TTL 在 58-60 之间(网络/时钟可能略偏)
    assert 58 <= ttl <= 60


def test_delete(fake_redis):
    """delete 移除 key"""
    s = CacheService()
    s.set("del:key", "x")
    assert s.exists("del:key") is True
    assert s.delete("del:key") is True
    assert s.exists("del:key") is False


def test_exists(fake_redis):
    """exists 检查 key"""
    s = CacheService()
    assert s.exists("nope") is False
    s.set("yes:key", 1)
    assert s.exists("yes:key") is True


def test_incr(fake_redis):
    """incr 原子递增 + 第一次设 TTL"""
    s = CacheService()
    n1 = s.incr("counter:key", ttl_seconds=60)
    n2 = s.incr("counter:key", ttl_seconds=60)
    n3 = s.incr("counter:key", ttl_seconds=60)
    assert (n1, n2, n3) == (1, 2, 3)
    # TTL 已设
    assert s.ttl("counter:key") > 0


def test_set_complex_types(fake_redis):
    """支持 dict / list / 嵌套"""
    s = CacheService()
    data = {
        "name": "test",
        "scores": [0.9, 0.8, 0.7],
        "meta": {"piece": "Bach", "tempo": 120},
    }
    s.set("complex", data)
    assert s.get("complex") == data


def test_set_when_unavailable():
    """Redis 不可用时 set 返回 False(不抛异常)"""
    s = CacheService()
    s._client = None
    s._enabled = False
    assert s.set("x", "y") is False
    assert s.get("x") is None
    assert s.delete("x") is False


# ──────────────────────────────────────────────
# 业务级辅助
# ──────────────────────────────────────────────
def test_midi_hash_deterministic(tmp_path):
    """同样 MIDI 同样 hash"""
    f1 = tmp_path / "a.mid"
    f1.write_bytes(b"x" * 100)
    h1 = CacheService.midi_hash(f1, "baroque")
    h2 = CacheService.midi_hash(f1, "baroque")
    assert h1 == h2
    assert len(h1) == 16  # md5[:16]


def test_midi_hash_differs_for_different_period(tmp_path):
    """不同 period → 不同 hash"""
    f = tmp_path / "a.mid"
    f.write_bytes(b"x" * 100)
    h1 = CacheService.midi_hash(f, "baroque")
    h2 = CacheService.midi_hash(f, "classical")
    assert h1 != h2


def test_midi_hash_missing_file():
    """文件不存在 → fallback hash"""
    h = CacheService.midi_hash("/tmp/nonexistent_xyz.mid", "")
    assert len(h) == 16


def test_eval_key_format(tmp_path):
    """eval_key 格式: eval:<hash>"""
    f = tmp_path / "x.mid"
    f.write_bytes(b"x")
    key = CacheService.eval_key(f, "baroque")
    assert key.startswith("eval:")
    assert len(key) == len("eval:") + 16


# ──────────────────────────────────────────────
# 端到端:评估缓存流
# ──────────────────────────────────────────────
def test_evaluation_cache_roundtrip(fake_redis, tmp_path):
    """存评估结果 → 取评估结果 → 数据一致"""
    s = CacheService()
    midi = tmp_path / "x.mid"
    midi.write_bytes(b"x" * 100)

    key = s.eval_key(midi, "baroque")
    payload = {
        "pitch_score": 0.95,
        "expressiveness_score": 0.88,
        "hand_pose_score": 0.82,
        "rhythm_score": 0.90,
        "sight_reading_score": 0.75,
        "overall_score": 0.86,
        "teaching_tips": ["good"],
        "duration_ms": 12,
    }
    s.set(key, payload, ttl_seconds=86400)

    retrieved = s.get(key)
    assert retrieved == payload
    assert s.ttl(key) > 86000  # 24h - 几秒


# ──────────────────────────────────────────────
# Singleton
# ──────────────────────────────────────────────
def test_cache_service_singleton():
    """cache_service 是单例"""
    from app.services.cache import cache_service as cs2
    assert cache_service is cs2


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(["pytest", __file__, "-v", "--tb=short"], cwd=str(BACKEND_DIR))
    sys.exit(result.returncode)
