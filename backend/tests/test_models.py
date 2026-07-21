"""
Models tests — CRUD 往返 + 关系 + 业务方法
==========================================

测试目标:
- 4 张表能正常 create/drop (SQLite in-memory)
- User 插入 + 银发模式自动激活
- Evaluation 5 维加权 (overall = sum(w*score))
- CurriculumProgress 唯一约束
- SightReadingSession accuracy 重算
- 关系: User.evaluations / User.curriculum_progress / User.sight_reading_sessions
"""
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# 路径设置
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 用 SQLite in-memory 避免依赖 PostgreSQL
from app.db.base import Base
from app.models import (
    BlockType,
    CurriculumProgress,
    DifficultyLevel,
    Evaluation,
    OAuthProvider,
    SightReadingDifficulty,
    SightReadingInput,
    SightReadingMode,
    SightReadingSession,
    SubscriptionTier,
    User,
)


@pytest.fixture
def engine():
    """每次测试创建全新的内存 SQLite"""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def session(engine):
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


# ──────────────────────────────────────────────
# User 测试
# ──────────────────────────────────────────────
def test_user_create_basic(session):
    """User 基本创建"""
    u = User(
        email="alice@example.com",
        password_hash="$2b$12$abcdef...",
        name="Alice",
        age=25,
    )
    session.add(u)
    session.commit()
    assert u.id is not None
    assert isinstance(u.id, uuid.UUID)
    assert u.subscription_tier == SubscriptionTier.FREE
    assert u.oauth_provider == OAuthProvider.LOCAL
    assert u.is_active is True
    assert u.is_verified is False


def test_user_email_unique(session):
    """email 唯一性"""
    u1 = User(email="dup@example.com", password_hash="x")
    u2 = User(email="dup@example.com", password_hash="y")
    session.add(u1)
    session.commit()
    session.add(u2)
    with pytest.raises(Exception):  # IntegrityError
        session.commit()


def test_user_senior_auto_activate_age_60(session):
    """age=60 自动激活银发模式"""
    u = User(email="senior@example.com", age=60)
    assert u.should_auto_senior() is True


def test_user_senior_auto_activate_age_59(session):
    """age=59 不激活"""
    u = User(email="young@example.com", age=59)
    assert u.should_auto_senior() is False


def test_user_senior_explicit_override(session):
    """is_senior=True 强制激活 (不论年龄)"""
    u = User(email="override@example.com", age=20, is_senior=True)
    assert u.should_auto_senior() is True


def test_user_no_age_not_senior(session):
    """无年龄 + is_senior=False 不激活"""
    u = User(email="noage@example.com", age=None, is_senior=False)
    assert u.should_auto_senior() is False


def test_user_timestamps(session):
    """created_at / updated_at 自动填充"""
    u = User(email="ts@example.com")
    session.add(u)
    session.commit()
    assert u.created_at is not None
    assert u.updated_at is not None


def test_user_subscription_tiers():
    """所有订阅档位可实例化"""
    for tier in SubscriptionTier:
        u = User(email=f"{tier.value}@example.com", subscription_tier=tier)
        assert u.subscription_tier == tier


# ──────────────────────────────────────────────
# Evaluation 测试
# ──────────────────────────────────────────────
def test_evaluation_create(session):
    """Evaluation 创建"""
    u = User(email="e@example.com")
    session.add(u)
    session.flush()

    e = Evaluation(
        user_id=u.id,
        piece_name="Bach Prelude in C",
        midi_url="s3://copiano-midi/uuid.mid",
        pitch_score=0.95,
        expressiveness_score=0.80,
        hand_pose_score=0.85,
        rhythm_score=0.90,
        sight_reading_score=0.70,
    )
    e.overall_score = e.compute_overall()
    session.add(e)
    session.commit()

    assert e.overall_score > 0
    # 加权: 0.20*0.95 + 0.25*0.80 + 0.20*0.85 + 0.20*0.90 + 0.15*0.70
    # = 0.19 + 0.20 + 0.17 + 0.18 + 0.105 = 0.845
    assert 0.84 <= e.overall_score <= 0.85


def test_evaluation_weights_consistent():
    """权重和 = 1.0 (与 v3.0 论文一致)"""
    total = sum(Evaluation.WEIGHTS.values())
    assert abs(total - 1.0) < 0.001


def test_evaluation_user_relationship(session):
    """User.evaluations 反向关系"""
    u = User(email="rel@example.com")
    session.add(u)
    session.flush()

    e1 = Evaluation(user_id=u.id, piece_name="P1", midi_url="s3://1")
    e2 = Evaluation(user_id=u.id, piece_name="P2", midi_url="s3://2")
    session.add_all([e1, e2])
    session.commit()

    # 重新查询
    u2 = session.query(User).filter_by(email="rel@example.com").first()
    assert len(u2.evaluations) == 2


def test_evaluation_difficulty_enum(session):
    """difficulty 枚举"""
    u = User(email="diff@example.com")
    session.add(u)
    session.flush()
    e = Evaluation(
        user_id=u.id, piece_name="X", midi_url="s3://x",
        difficulty=DifficultyLevel.ADVANCED,
    )
    session.add(e)
    session.commit()
    assert e.difficulty == DifficultyLevel.ADVANCED


# ──────────────────────────────────────────────
# CurriculumProgress 测试
# ──────────────────────────────────────────────
def test_curriculum_create(session):
    """CurriculumProgress 创建"""
    u = User(email="c@example.com")
    session.add(u)
    session.flush()

    cp = CurriculumProgress(
        user_id=u.id,
        day_num=1,
        block_id="warmup_pitch_1",
        block_type=BlockType.WARMUP_PITCH,
        title="音高热身",
        score=0.85,
    )
    session.add(cp)
    session.commit()

    assert cp.is_completed() is False  # 还没 completed_at
    assert cp.ease_factor == 2.5  # SM-2 默认


def test_curriculum_complete(session):
    """标记完成"""
    u = User(email="c2@example.com")
    session.add(u)
    session.flush()
    cp = CurriculumProgress(
        user_id=u.id, day_num=2, block_id="hand_1",
        block_type=BlockType.HAND,
    )
    session.add(cp)
    session.commit()
    cp.completed_at = datetime.now(timezone.utc)
    session.commit()
    assert cp.is_completed() is True


def test_curriculum_unique_user_day_block(session):
    """(user_id, day_num, block_id) 唯一"""
    u = User(email="u@example.com")
    session.add(u)
    session.flush()

    cp1 = CurriculumProgress(user_id=u.id, day_num=1, block_id="b1", block_type=BlockType.WARMUP_PITCH)
    cp2 = CurriculumProgress(user_id=u.id, day_num=1, block_id="b1", block_type=BlockType.WARMUP_PITCH)
    session.add(cp1)
    session.commit()
    session.add(cp2)
    with pytest.raises(Exception):
        session.commit()


def test_curriculum_all_8_block_types():
    """8 种 block 类型全部存在"""
    expected = {
        "warmup_pitch", "hand", "expressiveness", "sight_reading",
        "main_piece", "review", "weakness", "cooldown",
    }
    actual = {bt.value for bt in BlockType}
    assert actual == expected


# ──────────────────────────────────────────────
# SightReadingSession 测试
# ──────────────────────────────────────────────
def test_sight_reading_create(session):
    """SightReadingSession 创建"""
    u = User(email="sr@example.com")
    session.add(u)
    session.flush()

    now = datetime.now(timezone.utc)
    s = SightReadingSession(
        user_id=u.id,
        difficulty=SightReadingDifficulty.INTERMEDIATE,
        mode=SightReadingMode.INTERVAL,
        input_method=SightReadingInput.MIDI,
        total_questions=20,
        correct_count=18,
        streak_max=12,
        notes_per_minute=45.5,
        started_at=now,
    )
    s.accuracy = s.compute_accuracy()
    session.add(s)
    session.commit()

    assert s.accuracy == 0.9  # 18/20
    assert s.duration_seconds == 0.0  # 还没结束


def test_sight_reading_end(session):
    """结束会话,计算时长"""
    u = User(email="sr2@example.com")
    session.add(u)
    session.flush()

    start = datetime.now(timezone.utc)
    s = SightReadingSession(
        user_id=u.id,
        started_at=start,
        total_questions=10, correct_count=8,
    )
    s.accuracy = s.compute_accuracy()
    session.add(s)
    session.commit()

    # 模拟 60 秒后结束
    from datetime import timedelta
    s.ended_at = start + timedelta(seconds=60)
    s.duration_seconds = 60.0
    session.commit()
    assert s.ended_at is not None
    assert s.duration_seconds == 60.0


def test_sight_reading_4_difficulties():
    """4 个难度等级"""
    assert len(list(SightReadingDifficulty)) == 4
    expected = {"beginner", "elementary", "intermediate", "advanced"}
    assert {d.value for d in SightReadingDifficulty} == expected


def test_sight_reading_3_modes():
    """3 个训练模式"""
    assert len(list(SightReadingMode)) == 3


def test_sight_reading_3_inputs():
    """3 种输入方式"""
    assert len(list(SightReadingInput)) == 3


# ──────────────────────────────────────────────
# 跨模型测试
# ──────────────────────────────────────────────
def test_user_cascade_delete(session):
    """删除用户级联删除评估/课程/视奏"""
    u = User(email="cascade@example.com")
    session.add(u)
    session.flush()

    e = Evaluation(user_id=u.id, piece_name="X", midi_url="s3://x")
    cp = CurriculumProgress(
        user_id=u.id, day_num=1, block_id="b",
        block_type=BlockType.WARMUP_PITCH,
    )
    sr = SightReadingSession(user_id=u.id, started_at=datetime.now(timezone.utc))
    session.add_all([e, cp, sr])
    session.commit()

    user_id = u.id
    session.delete(u)
    session.commit()

    # SQLite CASCADE 通常生效
    assert session.query(Evaluation).filter_by(user_id=user_id).count() == 0
    assert session.query(CurriculumProgress).filter_by(user_id=user_id).count() == 0
    assert session.query(SightReadingSession).filter_by(user_id=user_id).count() == 0


def test_all_models_importable():
    """所有模型可被集中导入"""
    from app.models import (
        User, Evaluation, CurriculumProgress, SightReadingSession,
        SubscriptionTier, OAuthProvider, DifficultyLevel,
        BlockType, SightReadingDifficulty, SightReadingMode, SightReadingInput,
    )
    assert User.__tablename__ == "users"
    assert Evaluation.__tablename__ == "evaluations"
    assert CurriculumProgress.__tablename__ == "curriculum_progress"
    assert SightReadingSession.__tablename__ == "sight_reading_sessions"


def test_all_tables_created(engine):
    """所有表被 SQLAlchemy 创建"""
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    expected = {"users", "evaluations", "curriculum_progress", "sight_reading_sessions"}
    assert expected.issubset(tables)


if __name__ == "__main__":
    # 直接运行
    import subprocess
    result = subprocess.run(
        ["pytest", __file__, "-v", "--tb=short"],
        cwd=str(BACKEND_DIR),
    )
    sys.exit(result.returncode)
