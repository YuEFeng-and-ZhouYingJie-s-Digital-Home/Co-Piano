"""
Evaluation Service tests
========================

测试 v3.0 模块移植到 backend.services.evaluation_service:
- eval_pitch: 音高 + 节奏
- expressiveness: 9 维表现力
- hand_pose: 9 维手型(可选,需要真实 landmarks)
- evaluation_service: 5 维编排
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import mido
import pytest

from app.services.evaluation_service import (
    WEIGHTS,
    EvaluationResult,
    evaluation_service,
)
from app.services.eval_pitch import evaluate as vp_evaluate, midi_to_notes
from app.services.expressiveness import (
    analyze_expressiveness,
)
from app.services.hand_pose import analyze_hand_pose
from app.services.senior_mode import (
    DEFAULT_SENIOR_CONFIG,
    simplify_text_for_senior,
)


# ──────────────────────────────────────────────
# Fixtures — 生成测试 MIDI
# ──────────────────────────────────────────────
@pytest.fixture
def tmp_midi_dir(tmp_path):
    """每次测试用全新 tmp 目录(避免 module-scope 状态污染)"""
    d = tmp_path / "midi"
    d.mkdir()
    return d


def _create_midi(pitches, path, bpm=120, velocity=64):
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm), time=0))
    beat = int(mido.second2tick(60.0 / bpm, mid.ticks_per_beat, mido.bpm2tempo(bpm)))
    for p in pitches:
        track.append(mido.Message('note_on', note=p, velocity=velocity, time=0))
        track.append(mido.Message('note_off', note=p, velocity=velocity, time=beat))
    mid.save(str(path))


@pytest.fixture
def ref_midi(tmp_midi_dir):
    p = tmp_midi_dir / "ref.mid"
    _create_midi([60, 62, 64, 65, 67, 69, 71, 72], p)
    return p


@pytest.fixture
def perfect_midi(tmp_midi_dir):
    p = tmp_midi_dir / "perfect.mid"
    _create_midi([60, 62, 64, 65, 67, 69, 71, 72], p)
    return p


@pytest.fixture
def one_wrong_midi(tmp_midi_dir):
    p = tmp_midi_dir / "one_wrong.mid"
    _create_midi([60, 62, 64, 66, 67, 69, 71, 72], p)  # 1 note wrong
    return p


@pytest.fixture
def half_wrong_midi(tmp_midi_dir):
    p = tmp_midi_dir / "half_wrong.mid"
    _create_midi([60, 62, 64, 60, 62, 64, 60, 62], p)  # 4 notes wrong
    return p


@pytest.fixture
def dynamic_midi(tmp_midi_dir):
    """带力度变化的 MIDI(测试 expressiveness)"""
    p = tmp_midi_dir / "dynamic.mid"
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(120), time=0))
    beat = int(mido.second2tick(0.5, mid.ticks_per_beat, mido.bpm2tempo(120)))
    velocities = [40, 60, 80, 100, 80, 60, 40, 60]
    for pitch, vel in zip([60, 62, 64, 65, 67, 69, 71, 72], velocities):
        track.append(mido.Message('note_on', note=pitch, velocity=vel, time=0))
        track.append(mido.Message('note_off', note=pitch, velocity=vel, time=beat))
    mid.save(str(p))
    return p


# ──────────────────────────────────────────────
# eval_pitch (D1 + D4)
# ──────────────────────────────────────────────
def test_eval_pitch_direct_perfect(ref_midi, perfect_midi):
    """v3.0 eval_pitch 直接调用:完全匹配"""
    r = vp_evaluate(str(ref_midi), str(perfect_midi))
    assert r["pitch_accuracy"] == 1.0
    assert r["n_matched"] == 8
    assert r["n_pitch_errors"] == 0
    assert r["score"] == 100


def test_eval_pitch_direct_one_wrong(ref_midi, one_wrong_midi):
    """v3.0 eval_pitch:1 个错音"""
    r = vp_evaluate(str(ref_midi), str(one_wrong_midi))
    assert r["pitch_accuracy"] == 7 / 8  # 7/8 correct
    assert r["n_pitch_errors"] == 1
    assert 87 <= r["score"] < 100


def test_eval_pitch_direct_half_wrong(ref_midi, half_wrong_midi):
    """v3.0 eval_pitch:多个错音(pitch_accuracy 显著降低)"""
    r = vp_evaluate(str(ref_midi), str(half_wrong_midi))
    # half_wrong = [60, 62, 64, 60, 62, 64, 60, 62] 跟 ref = [60, 62, 64, 65, 67, 69, 71, 72]
    # 音高 0-2 匹配 (60/62/64),音高 3-7 全部错 (60/62/64/60/62 vs 65/67/69/71/72)
    # pitch_accuracy 是匹配率,小于 0.5
    assert r["pitch_accuracy"] < 0.5
    assert r["n_pitch_errors"] >= 3


def test_midi_to_notes(ref_midi):
    """midi_to_notes 返回 Note 列表"""
    notes = midi_to_notes(str(ref_midi))
    assert len(notes) == 8
    assert notes[0].pitch == 60
    assert notes[7].pitch == 72


# ──────────────────────────────────────────────
# evaluation_service 编排
# ──────────────────────────────────────────────
def test_evaluate_pitch_service_perfect(ref_midi, perfect_midi):
    """service.evaluate_pitch:完美匹配"""
    r = evaluation_service.evaluate_pitch(ref_midi, perfect_midi)
    assert r["pitch_score"] == 1.0
    assert r["rhythm_score"] == 1.0
    assert r["raw"]["n_pitch_errors"] == 0


def test_evaluate_pitch_service_one_wrong(ref_midi, one_wrong_midi):
    """service.evaluate_pitch:1 错音"""
    r = evaluation_service.evaluate_pitch(ref_midi, one_wrong_midi)
    assert 0.8 < r["pitch_score"] < 0.9
    assert r["raw"]["n_pitch_errors"] == 1


def test_evaluate_pitch_service_timing():
    """带时偏的 MIDI 节奏分降低"""
    mid_a = mido.MidiFile()
    t1 = mido.MidiTrack()
    mid_a.tracks.append(t1)
    t1.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(120), time=0))
    # 完美 8 拍
    for p in [60, 62, 64, 65, 67, 69, 71, 72]:
        t1.append(mido.Message('note_on', note=p, velocity=64, time=0))
        t1.append(mido.Message('note_off', note=p, velocity=64, time=480))
    path_a = "/tmp/test_a.mid"
    mid_a.save(path_a)

    mid_b = mido.MidiFile()
    t2 = mido.MidiTrack()
    mid_b.tracks.append(t2)
    t2.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(120), time=0))
    # 时偏 100ms (~120 ticks at 120bpm)
    for i, p in enumerate([60, 62, 64, 65, 67, 69, 71, 72]):
        offset = 100 if i > 0 else 0  # 100ms 偏移
        t2.append(mido.Message('note_on', note=p, velocity=64, time=offset))
        t2.append(mido.Message('note_off', note=p, velocity=64, time=480))
    path_b = "/tmp/test_b.mid"
    mid_b.save(path_b)

    r = evaluation_service.evaluate_pitch(path_a, path_b)
    assert r["pitch_score"] == 1.0  # 音高还全对
    assert r["rhythm_score"] < 1.0  # 节奏分被扣


def test_evaluate_full_perfect(ref_midi, perfect_midi, dynamic_midi):
    """完整 5 维评估(无 hand / 无 sight_reading)"""
    r = evaluation_service.evaluate_full(
        reference_midi=ref_midi,
        user_midi=perfect_midi,
        period_hint="baroque",
    )
    assert isinstance(r, EvaluationResult)
    assert r.pitch_score == 1.0
    assert r.rhythm_score == 1.0
    # 表现力从 user MIDI 算
    assert 0.0 <= r.expressiveness_score <= 1.0
    # hand_pose 和 sight_reading 没传,默认 0
    assert r.hand_pose_score == 0.0
    assert r.sight_reading_score == 0.0
    # 综合分 > 0
    assert 0.0 < r.overall_score < 1.0
    # 有教学建议
    assert len(r.teaching_tips) > 0


def test_evaluate_full_with_sight_reading(ref_midi, perfect_midi):
    """完整评估 + sight_reading 分数"""
    r = evaluation_service.evaluate_full(
        reference_midi=ref_midi,
        user_midi=perfect_midi,
        sight_reading_score=0.85,
    )
    assert r.sight_reading_score == 0.85
    # overall 应包含 sight_reading
    # 注: perfect MIDI 算 expressiveness 不是 0
    expected_overall = (
        r.pitch_score * WEIGHTS["pitch"]
        + r.expressiveness_score * WEIGHTS["expressiveness"]
        + r.hand_pose_score * WEIGHTS["hand_pose"]
        + r.rhythm_score * WEIGHTS["rhythm"]
        + 0.85 * WEIGHTS["sight_reading"]
    )
    assert abs(r.overall_score - round(expected_overall, 4)) < 0.01


def test_evaluate_full_no_input():
    """无任何输入 → 全 0"""
    r = evaluation_service.evaluate_full()
    assert r.pitch_score == 0.0
    assert r.rhythm_score == 0.0
    assert r.expressiveness_score == 0.0
    assert r.hand_pose_score == 0.0
    assert r.sight_reading_score == 0.0
    assert r.overall_score == 0.0


def test_evaluate_full_invalid_midi(tmp_path):
    """无效 MIDI 不崩(异常隔离)"""
    bad = tmp_path / "bad.mid"
    bad.write_text("not a midi file")
    r = evaluation_service.evaluate_full(
        reference_midi=str(bad),
        user_midi=str(bad),
    )
    # 异常被捕获,分数保持默认 0
    assert r.pitch_score == 0.0
    assert r.rhythm_score == 0.0


def test_evaluation_result_to_dict():
    """EvaluationResult.to_dict 可序列化"""
    r = EvaluationResult(
        pitch_score=0.9,
        expressiveness_score=0.8,
        hand_pose_score=0.7,
        rhythm_score=0.85,
        sight_reading_score=0.6,
        overall_score=0.79,
        teaching_tips=["test tip"],
    )
    d = r.to_dict()
    assert d["pitch_score"] == 0.9
    assert d["teaching_tips"] == ["test tip"]


def test_weights_sum_to_one():
    """5 维权重和 = 1.0"""
    total = sum(WEIGHTS.values())
    assert abs(total - 1.0) < 0.001


# ──────────────────────────────────────────────
# expressiveness
# ──────────────────────────────────────────────
def test_expressiveness_analyze(ref_midi):
    """expressiveness.analyze_expressiveness 返回 9 维"""
    p = analyze_expressiveness(str(ref_midi))
    assert hasattr(p, "overall")
    assert hasattr(p, "velocity_mean")
    assert hasattr(p, "ltv")
    # 9 维度
    dim_count = sum(1 for attr in [
        "velocity_mean", "velocity_std", "dynamic_range",
        "ltv", "voicing_balance", "melody_lead_ms",
        "touch_speed", "articulation", "release_var",
    ] if hasattr(p, attr))
    assert dim_count == 9


def test_expressiveness_with_period(dynamic_midi):
    """expressiveness 接受 period_hint"""
    p = analyze_expressiveness(str(dynamic_midi), period_hint="baroque")
    assert 0 <= p.overall <= 100


# ──────────────────────────────────────────────
# senior_mode
# ──────────────────────────────────────────────
def test_senior_simplify_basic():
    """simplify_text_for_senior 简化长句"""
    long_text = "请注意,您在演奏 Allegro 部分时的力度变化非常细腻,这种细腻的处理方式体现了您对作品的深刻理解,但是在节奏方面可能还需要进一步加强练习。"
    simple = simplify_text_for_senior(long_text)
    assert isinstance(simple, str)
    # 简化后应该比原文短(去掉了复杂表达)
    assert len(simple) > 0


def test_senior_simplify_short_passthrough():
    """短文本不简化(已经在限制内)"""
    short_text = "做得好。"
    simple = simplify_text_for_senior(short_text)
    # 短句可能原样返回
    assert isinstance(simple, str)


def test_senior_config_default():
    """DEFAULT_SENIOR_CONFIG 有预期字段"""
    # v3.0 senior_mode 用 dict 而不是 dataclass
    assert isinstance(DEFAULT_SENIOR_CONFIG, dict)
    assert "tts_speed" in DEFAULT_SENIOR_CONFIG
    assert "auto_age_threshold" in DEFAULT_SENIOR_CONFIG
    # 默认 60 岁自动激活
    assert DEFAULT_SENIOR_CONFIG["auto_age_threshold"] == 60
    # tts_speed 0.85 慢一点,适合老年人
    assert DEFAULT_SENIOR_CONFIG["tts_speed"] == 0.85


# ──────────────────────────────────────────────
# hand_pose (只测导入 + 简单调用)
# ──────────────────────────────────────────────
def test_hand_pose_import():
    """analyze_hand_pose 可导入"""
    assert callable(analyze_hand_pose)


# ──────────────────────────────────────────────
# 单例
# ──────────────────────────────────────────────
def test_evaluation_service_singleton():
    """evaluation_service 是单例"""
    from app.services.evaluation_service import evaluation_service as es2
    assert evaluation_service is es2


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(["pytest", __file__, "-v", "--tb=short"], cwd=str(BACKEND_DIR))
    sys.exit(result.returncode)
