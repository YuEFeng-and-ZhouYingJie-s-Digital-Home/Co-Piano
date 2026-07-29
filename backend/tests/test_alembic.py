"""
Alembic migration tests
========================

测试目标:
- alembic.ini + env.py 配置正确
- 初始 migration 创建 4 张表 + 索引
- upgrade head / downgrade base 双向
- alembic_version 表追踪当前 revision
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import os
import sqlite3
import subprocess
import tempfile


def _run_alembic(args, db_url, cwd=None):
    """运行 alembic 命令,设置 DATABASE_URL_SYNC env var"""
    env = os.environ.copy()
    env["DATABASE_URL_SYNC"] = db_url
    return subprocess.run(
        ["alembic"] + args,
        cwd=cwd or str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )


def test_alembic_config_exists():
    """alembic.ini + env.py 存在"""
    assert (BACKEND_DIR / "alembic.ini").exists()
    assert (BACKEND_DIR / "alembic" / "env.py").exists()
    assert (BACKEND_DIR / "alembic" / "versions").is_dir()


def test_alembic_env_uses_base_metadata():
    """env.py 引用 Base.metadata"""
    env_py = (BACKEND_DIR / "alembic" / "env.py").read_text()
    assert "from app.db.base import Base" in env_py
    assert "target_metadata = Base.metadata" in env_py
    assert "import app.models" in env_py  # 触发所有模型注册


def test_migration_creates_all_tables():
    """upgrade head 在 SQLite 创建 4 张业务表"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        db_url = f"sqlite:///{db_path}"
        result = _run_alembic(["upgrade", "head"], db_url)
        assert result.returncode == 0, result.stderr
        # alembic 输出在 stderr
        assert "Running upgrade" in result.stderr

        # 验证表
        conn = sqlite3.connect(db_path)
        try:
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
        finally:
            conn.close()

        expected = {
            "users",
            "evaluations",
            "curriculum_progress",
            "sight_reading_sessions",
            "alembic_version",
        }
        assert expected.issubset(tables), f"Missing: {expected - tables}"
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_migration_creates_indexes():
    """upgrade head 创建预期索引"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        db_url = f"sqlite:///{db_path}"
        _run_alembic(["upgrade", "head"], db_url)

        conn = sqlite3.connect(db_path)
        try:
            # users 表索引
            indexes = {row[1] for row in conn.execute(
                "SELECT * FROM sqlite_master WHERE type='index' AND tbl_name='users'"
            )}
            assert any("email" in str(idx) for idx in indexes)
        finally:
            conn.close()
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_downgrade_drops_tables():
    """downgrade base 删除所有业务表"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        db_url = f"sqlite:///{db_path}"
        # upgrade
        _run_alembic(["upgrade", "head"], db_url)
        # downgrade
        result = _run_alembic(["downgrade", "base"], db_url)
        assert result.returncode == 0, result.stderr

        conn = sqlite3.connect(db_path)
        try:
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'alembic%'"
            )}
        finally:
            conn.close()

        # 业务表应全部消失
        assert tables == set() or tables == set(), f"残留表: {tables}"
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_alembic_current_tracks_revision():
    """alembic current 报告当前 revision"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        db_url = f"sqlite:///{db_path}"
        # 跑 upgrade
        _run_alembic(["upgrade", "head"], db_url)
        # current 应返回 head revision
        result = _run_alembic(["current"], db_url)
        assert result.returncode == 0, result.stderr
        assert "(head)" in result.stdout
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_roundtrip_idempotent():
    """upgrade 在已有 DB 上是 no-op(不会重复建表)"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        db_url = f"sqlite:///{db_path}"
        _run_alembic(["upgrade", "head"], db_url)
        # 再跑一次不应报错
        result = _run_alembic(["upgrade", "head"], db_url)
        assert result.returncode == 0
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_migration_files_have_required_structure():
    """migration 文件包含必要结构"""
    versions_dir = BACKEND_DIR / "alembic" / "versions"
    migrations = list(versions_dir.glob("*.py"))
    assert len(migrations) >= 1, "至少应有 1 个 migration"

    for mig in migrations:
        content = mig.read_text()
        # 必须有 revision / down_revision / upgrade / downgrade
        assert "revision:" in content
        assert "down_revision" in content
        assert "def upgrade()" in content
        assert "def downgrade()" in content


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(["pytest", __file__, "-v", "--tb=short"], cwd=str(BACKEND_DIR))
    sys.exit(result.returncode)
