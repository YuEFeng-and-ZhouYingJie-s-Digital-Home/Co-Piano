"""
gen_test_midi.py — 生成两段 MIDI(参考 vs 用户)做 eval_pitch 测试

参考: C major scale C4-D4-E4-F4-G4-A4-B4-C5(每音 0.5s, 力度 80)
用户: C major scale C4-D4-E4-F4-G4-A4-B4-C5(每音 0.5s, 力度 60-80, 节奏漂移 +30ms, 第三个音错成 D#4)
"""
import pretty_midi

def gen(out, notes, tempo_bpm=120):
    pm = pretty_midi.PrettyMIDI(initial_tempo=tempo_bpm)
    inst = pretty_midi.Instrument(program=0)
    t = 0.0
    beat = 60.0 / tempo_bpm
    for pitch, vel, dur_beat in notes:
        note = pretty_midi.Note(velocity=vel, pitch=pitch, start=t, end=t + dur_beat * beat)
        inst.notes.append(note)
        t += dur_beat * beat
    pm.instruments.append(inst)
    pm.write(out)

# C major scale, 8 个音, 各 1 beat, 力度 80
ref = [(60, 80, 1), (62, 80, 1), (64, 80, 1), (65, 80, 1), (67, 80, 1), (69, 80, 1), (71, 80, 1), (72, 80, 1)]
gen('/tmp/test_ref.mid', ref)

# 用户:第 3 音错成 D# (63),力度不均,节奏略快
user = [
    (60, 70, 0.95),  # 略快
    (62, 75, 1.0),
    (63, 65, 1.05),  # 错音 D# 替代 E
    (65, 70, 1.0),
    (67, 60, 1.0),   # 弱
    (69, 70, 1.0),
    (71, 75, 1.0),
    (72, 85, 1.0),   # 强结尾
]
gen('/tmp/test_user.mid', user)

print("✓ /tmp/test_ref.mid + /tmp/test_user.mid")
