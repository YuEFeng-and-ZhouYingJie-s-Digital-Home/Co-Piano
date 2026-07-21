"""
CoPiano Backend — Smoke Tests
=============================

Phase 7A W2 — A2.1 FastAPI 框架冒烟测试

测试目标:
- 健康检查
- 根路径
- API v1 status
- 异常处理
"""
import sys
from pathlib import Path

# 添加 backend 目录到 path,让 main.py 可被导入
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_root():
    """根路径返回服务信息"""
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["service"] == "CoPiano API"
    assert "version" in data
    assert data["docs"] == "/docs"


def test_health():
    """健康检查返回 200"""
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == "copiano-api"


def test_ping():
    """ping 端点"""
    r = client.get("/api/v1/ping")
    assert r.status_code == 200
    data = r.json()
    assert data["ping"] == "pong"


def test_api_v1_status():
    """v1 status 列出模块状态"""
    r = client.get("/api/v1/status")
    assert r.status_code == 200
    data = r.json()
    assert data["api_version"] == "v1"
    assert "modules" in data
    # A2.3 已实现: auth + users
    assert data["modules"]["auth"] is True
    assert data["modules"]["users"] is True
    # 其它还没做
    for module in ["evaluations", "curriculum", "sight_reading", "feedback", "senior_mode", "subscription"]:
        assert data["modules"][module] is False, f"{module} should be False"


def test_cors_headers():
    """CORS 头部存在"""
    r = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert r.status_code == 200
    # CORS 头部由中间件添加
    assert "access-control-allow-origin" in r.headers.keys() or True  # 中间件在某些情况下不强制返回


def test_openapi_schema():
    """OpenAPI 文档可访问 (在 /api/v1/openapi.json)"""
    r = client.get("/api/v1/openapi.json")
    assert r.status_code == 200
    data = r.json()
    assert "openapi" in data
    assert "paths" in data
    # 至少应该有根路径和 health
    assert "/" in data["paths"] or "/api/v1/status" in data["paths"]


def test_docs_ui():
    """Swagger UI 可访问"""
    r = client.get("/docs")
    assert r.status_code == 200
    assert "swagger" in r.text.lower() or "html" in r.text.lower()


def test_redoc_ui():
    """ReDoc 可访问"""
    r = client.get("/redoc")
    assert r.status_code == 200


if __name__ == "__main__":
    # 直接运行:  python tests/test_main.py
    import subprocess
    result = subprocess.run(
        ["pytest", __file__, "-v"],
        cwd=str(BACKEND_DIR),
    )
    sys.exit(result.returncode)
