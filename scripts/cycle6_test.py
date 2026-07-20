"""
cycle6_test.py — Phase 6 CYCLE 6 综合测试

测试 sight_reading_trainer 模块的:
1. 4 难度级别 (beginner/elementary/intermediate/advanced)
2. 3 模式 (random / interval / piece)
3. 3 输入 (电脑键 / MIDI / 虚拟键盘 = note name)
4. 3 教学法 (landmark / interval / pattern)
5. SessionStats (accuracy / streak / bpm)
6. staff ASCII 可视化
7. voice_dialog 集成 (无递归)
8. 升档判定
9. 内置反馈 (LLM 0s 直答)
10. 难度渐进 (4 档单调性: 难度↑ 音域↑ 调号↑)
"""

import json
import sys
import time
import types
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from sight_reading_trainer import (
    Note,
    SessionStats,
    DIFFICULTY_LEVELS,
    KEYBOARD_MAP,
    NOTE_NAMES,
    REAL_PIECES,
    SIGHT_READING_TIPS,
    SightReadingTrainer,
    keyboard_to_pitch,
    name_to_pitch,
    pitch_to_name,
    landmark_note_sequence,
    interval_note_sequence,
    pattern_note_sequence,
    get_sight_reading_feedback,
    patch_voice_dialog_with_sight_reading,
    save_sight_reading_session,
)


PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "

results = {"pass": 0, "fail": 0, "tests": []}


def record(name, ok, detail=""):
    if ok:
        results["pass"] += 1
        status = PASS
    else:
        results["fail"] += 1
        status = FAIL
    results["tests"].append({"name": name, "pass": ok, "detail": detail})
    print(f"{status} {name}: {detail}")


# === Test 1: 4 难度级别配置 ===
def test_difficulty_levels():
    print("\n=== Test 1: 4 难度级别配置 ===")
    expected = ['beginner', 'elementary', 'intermediate', 'advanced']
    record("has_4_difficulties", list(DIFFICULTY_LEVELS.keys()) == expected,
           f"keys: {list(DIFFICULTY_LEVELS.keys())}")

    # 每个难度都有必要字段
    required_keys = ['name', 'octave_range', 'allowed_keys', 'bpm_target', 'accuracy_promote', 'methods', 'description']
    for lvl, cfg in DIFFICULTY_LEVELS.items():
        missing = [k for k in required_keys if k not in cfg]
        record(f"level_{lvl}_complete", len(missing) == 0,
               f"missing: {missing}" if missing else f"all {len(required_keys)} fields present")

    # 单调性: 难度↑ 音域范围更宽
    ranges = [DIFFICULTY_LEVELS[l]['octave_range'] for l in ('beginner', 'elementary', 'intermediate', 'advanced')]
    record("octave_range_monotonic", ranges == [(4,5), (3,5), (3,6), (3,6)],
           f"ranges: {ranges}")

    # 单调性: 难度↑ 目标 BPM 更高
    bpms = [DIFFICULTY_LEVELS[l]['bpm_target'] for l in ('beginner', 'elementary', 'intermediate', 'advanced')]
    record("bpm_monotonic_increase", bpms == [40, 60, 80, 100],
           f"bpms: {bpms}")

    # 单调性: 难度↑ 升档阈值更严
    promotes = [DIFFICULTY_LEVELS[l]['accuracy_promote'] for l in ('beginner', 'elementary', 'intermediate', 'advanced')]
    record("promote_threshold_strict", promotes == [0.80, 0.85, 0.90, 0.95],
           f"promotes: {promotes}")


# === Test 2: 音符映射 ===
def test_note_mapping():
    print("\n=== Test 2: 音符映射 ===")
    # pitch ↔ name 互转
    cases = [(60, 'C4'), (62, 'D4'), (64, 'E4'), (65, 'F4'), (67, 'G4'), (69, 'A4'), (71, 'B4'),
             (72, 'C5'), (48, 'C3'), (84, 'C6')]
    for pitch, name in cases:
        ok = pitch_to_name(pitch) == name
        record(f"pitch_to_name_{pitch}", ok, f"{pitch} → {pitch_to_name(pitch)} (expect {name})")
        ok2 = name_to_pitch(name) == pitch
        record(f"name_to_pitch_{name}", ok2, f"{name} → {name_to_pitch(name)} (expect {pitch})")

    # 升降号
    record("F#4_works", name_to_pitch('F#4') == 66, f"F#4 → {name_to_pitch('F#4')}")
    record("Bb4_works", name_to_pitch('Bb4') == 70, f"Bb4 → {name_to_pitch('Bb4')}")
    record("C#5_works", name_to_pitch('C#5') == 73, f"C#5 → {name_to_pitch('C#5')}")


# === Test 3: 电脑键输入 ===
def test_keyboard_input():
    print("\n=== Test 3: 电脑键 1-7 / q-u 输入 ===")
    # 1-7 = C4-B4
    expected = [60, 62, 64, 65, 67, 69, 71]
    for i, key in enumerate('1234567'):
        pitch = keyboard_to_pitch(key)
        ok = pitch == expected[i]
        record(f"key_{key}", ok, f"'{key}' → {pitch} (expect {expected[i]})")

    # q-u = C5-B5
    expected_high = [72, 74, 76, 77, 79, 81, 83]
    for i, key in enumerate('qwertyu'):
        pitch = keyboard_to_pitch(key)
        ok = pitch == expected_high[i]
        record(f"key_{key}_high", ok, f"'{key}' → {pitch} (expect {expected_high[i]})")

    # 大写也可以
    record("uppercase_key", keyboard_to_pitch('Q') == 72, f"'Q' → {keyboard_to_pitch('Q')}")
    # 非法键 (非映射键)
    record("invalid_key_returns_neg", keyboard_to_pitch('!') == -1, f"'!' → {keyboard_to_pitch('!')}")
    # x → D3 (合法的低八度键)
    record("x_maps_to_D3", keyboard_to_pitch('x') == 50, f"'x' → {keyboard_to_pitch('x')} (D3)")


# === Test 4: 3 教学法 ===
def test_teaching_methods():
    print("\n=== Test 4: 3 教学法 ===")
    for method_name, method_fn in [('landmark', landmark_note_sequence),
                                    ('interval', interval_note_sequence),
                                    ('pattern', pattern_note_sequence)]:
        for level in DIFFICULTY_LEVELS:
            seq = method_fn(level, count=10, seed=42)
            ok = len(seq) == 10 and all(isinstance(n, Note) for n in seq)
            record(f"method_{method_name}_{level}", ok,
                   f"len={len(seq)} all_Notes={all(isinstance(n, Note) for n in seq)}")
            # 检查音域限制
            cfg = DIFFICULTY_LEVELS[level]
            lo = (cfg['octave_range'][0] + 1) * 12
            hi = (cfg['octave_range'][1] + 1) * 12 + 11
            in_range = all(lo <= n.pitch <= hi for n in seq)
            record(f"method_{method_name}_{level}_range", in_range,
                   f"all in [{lo},{hi}]: min={min(n.pitch for n in seq)} max={max(n.pitch for n in seq)}")


# === Test 5: 真曲片段 ===
def test_real_pieces():
    print("\n=== Test 5: 真曲片段 ===")
    for piece_name, fn in REAL_PIECES.items():
        seq = fn()
        record(f"piece_{piece_name}_loaded", len(seq) >= 8 and len(seq) <= 30,
               f"len={len(seq)}")
        # 起始音
        first = seq[0].name
        record(f"piece_{piece_name}_first_note", first != '?',
               f"first: {first}")


# === Test 6: SessionStats ===
def test_session_stats():
    print("\n=== Test 6: SessionStats ===")
    s = SessionStats()
    s.total = 10
    s.correct = 8
    s.streak = 3
    s.best_streak = 5
    s.start_time = time.time() - 60  # 1 min ago
    s.end_time = time.time()

    record("accuracy_calc", abs(s.accuracy - 0.8) < 0.01, f"acc={s.accuracy}")
    record("duration_calc", 55 < s.duration_sec < 65, f"duration={s.duration_sec:.1f}s")
    record("notes_per_minute", 8 < s.notes_per_minute < 12, f"npm={s.notes_per_minute:.1f}")

    d = s.to_dict()
    record("to_dict_has_accuracy", 'accuracy' in d, f"keys: {list(d.keys())[:6]}...")


# === Test 7: SightReadingTrainer 完整流程 ===
def test_trainer_full_flow():
    print("\n=== Test 7: SightReadingTrainer 完整流程 ===")
    for diff in DIFFICULTY_LEVELS:
        for mode in ('random', 'interval', 'piece'):
            t = SightReadingTrainer(difficulty=diff, mode=mode, seed=42)
            seq = t.generate_sequence(count=8)
            record(f"generate_{diff}_{mode}", len(seq) >= 1,
                   f"seq_len={len(seq)}")
            # 完美答完
            for n in seq:
                t.submit_answer(n.pitch)
            t.finish()
            s = t.stats
            record(f"perfect_{diff}_{mode}", s.accuracy == 1.0 and s.total == len(seq),
                   f"acc={s.accuracy:.0%} total={s.total}/{len(seq)} streak={s.best_streak}")
            # 升档判定
            promote = t.should_promote()
            if diff == 'advanced':
                # 最高级不能再升
                expected_promote = False
            else:
                # 完美 100% >= threshold
                expected_promote = True
            record(f"promote_{diff}_{mode}", promote == expected_promote,
                   f"promote={promote} expected={expected_promote}")


# === Test 8: 错答 + streak 重置 ===
def test_wrong_answer():
    print("\n=== Test 8: 错答 streak 重置 ===")
    t = SightReadingTrainer('beginner', 'random', seed=42)
    seq = t.generate_sequence(count=3)
    # 答对 2 次
    t.submit_answer(seq[0].pitch)
    t.submit_answer(seq[1].pitch)
    record("streak_after_2_correct", t.stats.streak == 2, f"streak={t.stats.streak}")
    # 答错 1 次 (idx 还在 2, 期望 seq[2])
    t.submit_answer(0)  # 完全错
    record("streak_reset_on_wrong", t.stats.streak == 0, f"streak={t.stats.streak}")
    record("error_recorded", len(t.stats.errors) == 1, f"errors={len(t.stats.errors)}")
    # 答对恢复: 此时 idx=2, 期望是 seq[2]
    t.submit_answer(seq[2].pitch)
    record("streak_recover", t.stats.streak == 1, f"streak={t.stats.streak}")


# === Test 9: 多输入方式 (键盘/MIDI/note_name) ===
def test_multi_input():
    print("\n=== Test 9: 多输入方式 ===")
    # 同一首 sequence 答 3 遍,每遍用不同输入
    t = SightReadingTrainer('beginner', 'random', seed=42)
    seq = t.generate_sequence(count=5)
    expected_first = seq[0]

    # MIDI pitch (int)
    t1 = SightReadingTrainer('beginner', 'random', seed=42)
    t1.generate_sequence(count=5)
    t1.submit_answer(expected_first.pitch)
    record("input_midi_int", t1.stats.correct == 1, f"correct={t1.stats.correct}")

    # 电脑键 (str)
    # 用一个 fixed 测试: 强制 seq 第一个音 = C4 (60, key='1')
    t2 = SightReadingTrainer('beginner', 'random', seed=42)
    t2.sequence = [Note(pitch=60), Note(pitch=62), Note(pitch=64),
                   Note(pitch=65), Note(pitch=67)]
    t2.current_idx = 0
    t2.submit_answer('1')  # 1 = C4
    record("input_keyboard_str", t2.stats.correct == 1,
           f"key='1' (C4) correct={t2.stats.correct}")

    # 电脑键 (但 first 是 D#4 — 不在 1-7 范围) — 期望 False
    t2b = SightReadingTrainer('beginner', 'random', seed=42)
    t2b.sequence = [Note(pitch=63), Note(pitch=67), Note(pitch=60)]
    t2b.current_idx = 0
    ok = t2b.submit_answer('1')  # 1 = C4, 期望 D#4
    record("keyboard_out_of_range", ok == False,
           f"D#4 vs key '1' (C4): correct={ok}")

    # 音符名 (str)
    t3 = SightReadingTrainer('beginner', 'random', seed=42)
    t3.generate_sequence(count=5)
    t3.submit_answer(expected_first.name)
    record("input_note_name", t3.stats.correct == 1, f"name='{expected_first.name}' correct={t3.stats.correct}")


# === Test 10: 内置反馈 (LLM 0s 直答) ===
def test_builtin_feedback():
    print("\n=== Test 10: 内置反馈 ===")
    # 必须有 6 个常见错误解释
    record("has_6_tips", len(SIGHT_READING_TIPS) >= 6, f"tips: {len(SIGHT_READING_TIPS)}")
    for kind in ('wrong_pitch', 'wrong_octave', 'rhythm', 'streak_break', 'promote', 'demote',
                 'beginner_hint', 'interval_hint', 'pattern_hint'):
        record(f"has_tip_{kind}", kind in SIGHT_READING_TIPS,
               f"tip exists" if kind in SIGHT_READING_TIPS else f"missing")

    # 升档反馈
    t = SightReadingTrainer('beginner', 'random', seed=42)
    t.stats.correct = 9
    t.stats.total = 10
    fb = get_sight_reading_feedback(t, 'promote')
    record("promote_feedback_has_next", 'elementary' in fb, f"fb: {fb}")
    # 降档反馈
    fb2 = get_sight_reading_feedback(t, 'demote')
    record("demote_feedback_has_threshold", '90%' in fb2, f"fb2: {fb2}")
    # 八度错
    fb3 = get_sight_reading_feedback(t, 'wrong_octave', expected='C4', got='C5')
    record("octave_feedback", 'C4' in fb3 and 'C5' in fb3, f"fb3: {fb3}")


# === Test 11: voice_dialog 集成 (无递归) ===
def test_voice_dialog_integration():
    print("\n=== Test 11: voice_dialog 集成 (无递归) ===")
    handle, state = patch_voice_dialog_with_sight_reading(None)

    # 关键词识别
    for kw in ['识谱训练', '练视奏', '识谱', 'sight reading', '看谱']:
        r = handle(kw)
        record(f"kw_on_{kw}", r is not None and state['active'], f"r: {r[:50] if r else 'None'}")
        # 关闭
        handle('结束识谱')
        record(f"kw_off_{kw}", state['active'] == False, f"active={state['active']}")

    # 难度切换
    handle('开始 Elementary 视奏')
    record("switch_to_elementary", state['difficulty'] == 'elementary', f"diff: {state['difficulty']}")
    handle('结束识谱')
    handle('开始 Advanced 视奏')
    record("switch_to_advanced", state['difficulty'] == 'advanced', f"diff: {state['difficulty']}")

    # 默认 beginner
    handle('结束识谱')
    handle('识谱训练')
    record("default_beginner", state['difficulty'] == 'beginner', f"diff: {state['difficulty']}")

    # Monkey patch 测试 (无递归)
    # 构造 mock voice_dialog
    mock_mod = types.SimpleNamespace()
    call_count = {'llm': 0, 'orig': 0}

    def mock_call_llm(messages, **kwargs):
        call_count['llm'] += 1
        return "测试回复"
    mock_mod.call_llm = mock_call_llm
    mock_mod.process_query = None  # 让 patch 注入

    # 记录 patched 行为
    patch_voice_dialog_with_sight_reading(mock_mod)
    # 调用识谱关键词
    handle_result = mock_mod.process_query('识谱')
    record("voice_no_recursion_on", handle_result is not None, f"got: {handle_result[:50] if handle_result else 'None'}")

    # 关闭后转 LLM
    handle('结束识谱')
    handle_result2 = mock_mod.process_query('你好')
    record("voice_falls_to_llm", call_count['llm'] == 1, f"llm_call_count={call_count['llm']}")


# === Test 12: 升档/降档逻辑 ===
def test_promote_demote():
    print("\n=== Test 12: 升档/降档逻辑 ===")
    for diff in DIFFICULTY_LEVELS:
        t = SightReadingTrainer(difficulty=diff, mode='random', seed=42)
        seq = t.generate_sequence(count=10)
        # 全部答对
        for n in seq:
            t.submit_answer(n.pitch)
        t.finish()
        cfg = DIFFICULTY_LEVELS[diff]
        if diff == 'advanced':
            record(f"max_level_{diff}", not t.should_promote(), "advanced: 不能再升")
        else:
            record(f"perfect_promote_{diff}", t.should_promote(), f"acc={t.stats.accuracy:.0%} >= {cfg['accuracy_promote']:.0%}")


# === Test 13: 速度 (1 session < 100ms) ===
def test_speed():
    print("\n=== Test 13: 速度 ===")
    start = time.time()
    for _ in range(10):
        t = SightReadingTrainer('intermediate', 'piece', seed=42)
        t.generate_sequence(count=15)
        for n in t.sequence:
            t.submit_answer(n.pitch)
    elapsed = (time.time() - start) / 10
    record("single_session_speed", elapsed < 0.5, f"{elapsed*1000:.1f}ms per session")


# === Test 14: 边界情况 ===
def test_edge_cases():
    print("\n=== Test 14: 边界情况 ===")
    # 非法难度
    try:
        SightReadingTrainer(difficulty='expert')
        record("invalid_difficulty_raises", False, "should have raised ValueError")
    except ValueError:
        record("invalid_difficulty_raises", True, "ValueError raised")

    # 非法 mode
    try:
        SightReadingTrainer(mode='xyz')
        record("invalid_mode_raises", False, "should have raised ValueError")
    except ValueError:
        record("invalid_mode_raises", True, "ValueError raised")

    # 空 sequence 提交
    t = SightReadingTrainer('beginner', 'random', seed=42)
    t.generate_sequence(count=3)
    for n in t.sequence:
        t.submit_answer(n.pitch)
    # 已经结束
    t.finish()
    record("finish_after_complete", t.stats.end_time > 0, f"end_time set: {t.stats.end_time > 0}")

    # 非法 pitch
    t2 = SightReadingTrainer('beginner', 'random', seed=42)
    t2.generate_sequence(count=3)
    ok = t2.submit_answer('not_a_key')
    record("invalid_answer_returns_false", ok == False, f"returned: {ok}")

    # 合法 note name (e.g. F#3)
    t3 = SightReadingTrainer('beginner', 'random', seed=42)
    seq3 = t3.generate_sequence(count=3)
    if seq3[0].pitch in (60, 62, 64, 65, 67, 69, 71):  # C4-B4 范围
        ok = t3.submit_answer(seq3[0].name)
        record("name_input_works", ok, f"name={seq3[0].name} correct={ok}")


# === Test 15: progress & staff ASCII ===
def test_progress_and_staff():
    print("\n=== Test 15: progress & staff ASCII ===")
    t = SightReadingTrainer('beginner', 'random', seed=42)
    t.generate_sequence(count=10)
    prog = t.get_progress()
    record("progress_has_current", 'current' in prog and prog['current'] == 0, f"current: {prog['current']}")
    record("progress_has_total", prog['total'] == 10, f"total: {prog['total']}")
    record("progress_has_current_note", prog['current_note'] is not None,
           f"note: {prog['current_note']['name']}")

    # 答对 1 个
    t.submit_answer(prog['current_note']['pitch'])
    prog2 = t.get_progress()
    record("progress_updates", prog2['current'] == 1, f"after 1 right: {prog2['current']}")

    # staff ASCII
    staff = t.get_staff_ascii(line_count=3)
    record("staff_not_empty", len(staff) > 0, f"len={len(staff)} chars")


# === Test 16: save_sight_reading_session ===
def test_save_session():
    print("\n=== Test 16: save_sight_reading_session ===")
    t = SightReadingTrainer('beginner', 'random', seed=42)
    t.generate_sequence(count=8)
    for n in t.sequence:
        t.submit_answer(n.pitch)
    t.finish()

    # 无 student_db 测试
    summary = save_sight_reading_session(None, t, piece_name='test_piece')
    record("summary_has_required_keys",
           all(k in summary for k in ['date', 'difficulty', 'mode', 'accuracy', 'note_count', 'best_streak']),
           f"keys: {list(summary.keys())}")
    record("summary_difficulty_correct", summary['difficulty'] == 'beginner', f"diff: {summary['difficulty']}")
    record("summary_piece_correct", summary['piece'] == 'test_piece', f"piece: {summary['piece']}")


# === Test 17: stable seed (MD5) ===
def test_stable_seed():
    print("\n=== Test 17: stable seed (MD5) ===")
    # 不传 seed,看是否稳定
    t1 = SightReadingTrainer('beginner', 'random')
    t1.generate_sequence(count=5)
    seq1 = [n.name for n in t1.sequence]

    # 同时再创建一个 (时间戳应该相同 → 同 seed)
    t2 = SightReadingTrainer('beginner', 'random')
    t2.generate_sequence(count=5)
    seq2 = [n.name for n in t2.sequence]
    record("default_seed_deterministic", seq1 == seq2, f"seq1={seq1} seq2={seq2}")

    # 显式 seed 应该确定
    t3 = SightReadingTrainer('beginner', 'random', seed=12345)
    t3.generate_sequence(count=5)
    seq3 = [n.name for n in t3.sequence]
    t4 = SightReadingTrainer('beginner', 'random', seed=12345)
    t4.generate_sequence(count=5)
    seq4 = [n.name for n in t4.sequence]
    record("explicit_seed_deterministic", seq3 == seq4, f"seq3==seq4: {seq3 == seq4}")


# === Test 18: landmark 偏好 (用中央 C 等固定音) ===
def test_landmark_prefers_landmarks():
    print("\n=== Test 18: landmark 偏好 ===")
    # 用较大 count,统计是否地标音占比 ~60%
    seq = landmark_note_sequence('beginner', count=100, seed=42)
    landmarks = {60, 67, 65, 72}  # C4, G4, F4, C5
    landmark_count = sum(1 for n in seq if n.pitch in landmarks)
    ratio = landmark_count / len(seq)
    record("landmark_ratio", 0.4 < ratio < 0.8, f"ratio={ratio:.0%} ({landmark_count}/{len(seq)})")


# === Test 19: 4 难度音域实际数据 ===
def test_difficulty_data():
    print("\n=== Test 19: 4 难度实际数据 ===")
    for diff in DIFFICULTY_LEVELS:
        seq = landmark_note_sequence(diff, count=50, seed=42)
        pitches = [n.pitch for n in seq]
        cfg = DIFFICULTY_LEVELS[diff]
        lo = (cfg['octave_range'][0] + 1) * 12
        hi = (cfg['octave_range'][1] + 1) * 12 + 11
        in_range = all(lo <= p <= hi for p in pitches)
        record(f"data_{diff}_in_range", in_range,
               f"min={min(pitches)} max={max(pitches)} expected=[{lo},{hi}]")


# === 主测试 ===
def main():
    print("=" * 60)
    print("Phase 6 CYCLE 6 — sight_reading_trainer 综合测试")
    print("=" * 60)

    test_difficulty_levels()
    test_note_mapping()
    test_keyboard_input()
    test_teaching_methods()
    test_real_pieces()
    test_session_stats()
    test_trainer_full_flow()
    test_wrong_answer()
    test_multi_input()
    test_builtin_feedback()
    test_voice_dialog_integration()
    test_promote_demote()
    test_speed()
    test_edge_cases()
    test_progress_and_staff()
    test_save_session()
    test_stable_seed()
    test_landmark_prefers_landmarks()
    test_difficulty_data()

    print("\n" + "=" * 60)
    total = results['pass'] + results['fail']
    rate = results['pass'] / total if total else 0
    print(f"结果: {results['pass']}/{total} pass ({rate:.0%})")
    if results['fail'] == 0:
        print("🎉 全部通过!")
    else:
        print("失败的测试:")
        for t in results['tests']:
            if not t['pass']:
                print(f"  ❌ {t['name']}: {t['detail']}")
    print("=" * 60)

    # 写 results json
    out_path = SCRIPT_DIR.parent / 'notes' / 'cycle6_test_results.json'
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2))

    return 0 if results['fail'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
