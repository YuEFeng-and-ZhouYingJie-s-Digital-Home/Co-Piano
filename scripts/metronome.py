"""
metronome.py — 终端 / 集成节拍器(解决 Flowkey/Simply Piano 用户痛点)

设计:
- 程序合成 click 声(无外部样本,跨平台)
- 4/4 / 3/4 / 6/8 拍号支持
- BPM 30-300
- 强拍/弱拍区别(强拍更响更高)
- 文字可视化(终端)
- 可集成 voice_dialog(教师喊拍子)

用法:
    python3 metronome.py --bpm 120 --beats 4                  # 跑 8 小节
    python3 metronome.py --bpm 90 --beats 3 --measures 16    # 3/4 拍 16 小节
    python3 metronome.py --bpm 60 --silent                   # 不出声,只跑循环
    from metronome import Metronome
    m = Metronome(bpm=120, beats=4)
    m.run_measures(8)
"""
from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


# ----- 声音合成 -----
def synthesize_click(sample_rate: int = 22050, duration_s: float = 0.04, accent: bool = False) -> np.ndarray:
    """合成 40ms 的 click 声

    - 强拍:1000Hz + 略长
    - 弱拍:800Hz + 略短
    - 快速衰减,听感像木鱼/click
    """
    n = int(duration_s * sample_rate)
    t = np.linspace(0, duration_s, n, endpoint=False)
    freq = 1000.0 if accent else 800.0
    # 正弦 + 快速指数衰减
    env = np.exp(-t * (60 if accent else 80))
    wave = np.sin(2 * np.pi * freq * t) * env
    # 强拍稍响
    amp = 0.7 if accent else 0.5
    return (wave * amp * 32767).astype(np.int16)


# ----- 节拍器核心 -----
@dataclass
class MetronomeState:
    bpm: int = 120
    beats: int = 4  # 拍号分子(分母固定 4)
    current_beat: int = 0  # 当前拍(0 到 beats-1)
    measure: int = 0
    start_time: float = 0.0
    is_accent: bool = True  # 第 1 拍是强拍


class Metronome:
    """节拍器(可发声 + 文字可视化)"""

    def __init__(self, bpm: int = 120, beats: int = 4, sample_rate: int = 22050, audio: bool = True):
        if not 30 <= bpm <= 300:
            raise ValueError(f"BPM 必须在 30-300,当前 {bpm}")
        if not 1 <= beats <= 12:
            raise ValueError(f"beats 必须在 1-12,当前 {beats}")

        self.state = MetronomeState(bpm=bpm, beats=beats)
        self.sample_rate = sample_rate
        self.audio = audio
        self.sr = sample_rate

        # 预生成 click
        self._click_weak = synthesize_click(sample_rate, accent=False)
        self._click_strong = synthesize_click(sample_rate, accent=True)

        # 音频输出
        self._sd = None
        if audio:
            try:
                import sounddevice as sd
                self._sd = sd
            except ImportError:
                print("⚠️  sounddevice 未装,降级为 silent 模式", file=sys.stderr)
                self.audio = False

    def _play_click(self, accent: bool):
        """播一个 click"""
        if not self.audio or self._sd is None:
            return
        click = self._click_strong if accent else self._click_weak
        self._sd.play(click, samplerate=self.sr, blocking=False)

    def _visual_beat(self, beat_num: int, total_beats: int):
        """终端可视化(无音频时也用)"""
        # 1 2 3 4 / | | | |
        marks = "●" * total_beats
        if beat_num == 0:
            # 强拍
            line = f"  {self.state.measure + 1:3d} | [{beat_num + 1}]" + " . " * (total_beats - 1) + "  | " + marks
        else:
            line = f"  {self.state.measure + 1:3d} |  {beat_num + 1} " + " . " * (total_beats - beat_num - 1) + "  | " + marks
        print(line, end="\r", flush=True)
        if beat_num == total_beats - 1:
            print()  # 换行

    def _beat_duration_s(self) -> float:
        return 60.0 / self.state.bpm

    def run_measures(self, n_measures: int = 8):
        """跑 N 小节"""
        if n_measures < 1:
            raise ValueError(f"measures 必须 ≥ 1,当前 {n_measures}")
        beat_dur = self._beat_duration_s()
        total_beats = n_measures * self.state.beats
        print(f"🥁 节拍器启动: {self.state.bpm} BPM, {self.state.beats}/4, 跑 {n_measures} 小节")
        print(f"   按 Ctrl-C 停止")
        print()
        try:
            for i in range(total_beats):
                beat = i % self.state.beats
                if beat == 0:
                    self.state.measure = i // self.state.beats
                self.state.current_beat = beat
                is_accent = (beat == 0)
                self._play_click(is_accent)
                self._visual_beat(beat, self.state.beats)
                time.sleep(beat_dur)
        except KeyboardInterrupt:
            print("\n⏹  停止")
            return
        print(f"\n✅ 完成 {n_measures} 小节")

    def run_loop(self):
        """无限循环(直到 Ctrl-C)"""
        beat_dur = self._beat_duration_s()
        print(f"🥁 节拍器循环模式: {self.state.bpm} BPM, {self.state.beats}/4")
        try:
            measure = 0
            beat = 0
            while True:
                is_accent = (beat == 0)
                self._play_click(is_accent)
                self._visual_beat(beat, self.state.beats)
                time.sleep(beat_dur)
                beat = (beat + 1) % self.state.beats
                if beat == 0:
                    measure += 1
        except KeyboardInterrupt:
            print("\n⏹  停止")

    def run_with_tapping(self, n_beats: int = 8, silent: bool = False):
        """模式:节拍器提示,用户跟着弹/唱(录音检测准确度)
        silent=True 时只跑节拍不录音
        """
        if silent:
            return self.run_measures(n_beats // self.state.beats)

        try:
            import sounddevice as sd
        except ImportError:
            print("❌ sounddevice 未装,跑: pip3 install sounddevice", file=sys.stderr)
            return

        beat_dur = self._beat_duration_s()
        print(f"🥁 跟着节拍器: 弹 {n_beats} 拍,看你的节奏准不准")
        print(f"   BPM: {self.state.bpm}, 拍号: {self.state.beats}/4")
        print()

        recorded = []
        for i in range(n_beats):
            beat = i % self.state.beats
            is_accent = (beat == 0)
            self._play_click(is_accent)

            # 录这一拍内是否有声音
            rec = sd.rec(
                int(beat_dur * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
            )
            sd.wait()
            recorded.append(rec.flatten())

            rms = np.sqrt(np.mean(rec ** 2))
            mark = "✓" if rms > 0.01 else "✗"
            print(f"  [{i+1}/{n_beats}] {mark} (RMS={rms:.4f})")
        return recorded


# ----- 集成 voice_dialog -----
def patch_voice_dialog_with_metronome():
    """注入节拍器到 voice_dialog — 用户说 '开节拍器' 启动"""
    import voice_dialog

    def with_metronome(messages, backend="mock", **kwargs):
        last_user = next((m for m in reversed(messages) if m["role"] == "user"), None)
        if last_user and "节拍器" in last_user["content"]:
            # 解析 BPM
            import re
            m = re.search(r"(\d{2,3})\s*BPM", last_user["content"], re.IGNORECASE)
            bpm = int(m.group(1)) if m else 120
            if not 30 <= bpm <= 300:
                bpm = 120

            # 解析拍号
            m2 = re.search(r"(\d)/(\d)", last_user["content"])
            beats = int(m2.group(1)) if m2 else 4

            mn = Metronome(bpm=bpm, beats=beats, audio=True)
            print(f"\n[metronome] 启动 {bpm} BPM {beats}/4 跑 8 小节 ...")
            mn.run_measures(8)
            return f"已经帮你跑了 8 小节 {bpm} BPM {beats}/4 拍,继续练!"

        return voice_dialog.call_llm(messages, backend=backend, **kwargs)

    voice_dialog.call_llm = with_metronome


# ----- CLI -----
def main():
    parser = argparse.ArgumentParser(description="终端节拍器(程序合成 click)")
    parser.add_argument("--bpm", type=int, default=120, help="BPM (30-300)")
    parser.add_argument("--beats", type=int, default=4, help="拍号分子 (1-12)")
    parser.add_argument("--measures", type=int, default=8, help="跑多少小节")
    parser.add_argument("--loop", action="store_true", help="无限循环")
    parser.add_argument("--silent", action="store_true", help="不出声,只显示")
    parser.add_argument("--tap", type=int, metavar="N", help="跟随节拍录音 N 拍")
    args = parser.parse_args()

    mn = Metronome(bpm=args.bpm, beats=args.beats, audio=not args.silent)
    if args.tap:
        mn.run_with_tapping(args.tap, silent=args.silent)
    elif args.loop:
        mn.run_loop()
    else:
        mn.run_measures(args.measures)


if __name__ == "__main__":
    main()
