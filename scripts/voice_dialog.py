"""
voice_dialog.py — CoPiano 实时语音对话陪练(端到端)

完整链路:
  麦克风 → Silero VAD 切片 → faster-whisper ASR → Qwen 7B 推理 → Edge-TTS → 扬声器

组件:
- 音频采集:sounddevice(麦克风) / soundfile(文件)
- 语音端点检测:Silero VAD(4MB 模型,实时)
- 语音识别:faster-whisper(支持自动语种)
- LLM 推理:Mac 本地小模型 / GPU 服务器 Qwen 7B(SSH)
- 语音合成:Edge-TTS(云端,免模型)
- 播放:pygame(支持流式)

模式:
- --text "..."     直接说这段文字(LLM 跳过,只 TTS)
- --listen N       录 N 秒麦克风,识别 + 走 LLM + TTS
- --chat           完整对话循环(听-想-说)
- --demo           演示模式(无 LLM,测试 ASR+TTS 闭环)
- --mock-llm       用本地规则代替 LLM(测试对话框架)

用法:
    python3 voice_dialog.py --text "你好,我是 CoPiano"
    python3 voice_dialog.py --demo
    python3 voice_dialog.py --chat --llm mac
    python3 voice_dialog.py --chat --llm gpu
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

# ----- 配置 -----
SAMPLE_RATE = 16000
VAD_THRESHOLD = 0.5          # Silero VAD 阈值(0-1,越高越严格)
VAD_MIN_SILENCE_MS = 500     # 静音多久算说完
VAD_SPEECH_PAD_MS = 300      # 语音前后 padding
MAX_RECORD_S = 30            # 最长录音

DEFAULT_LLM_PROMPT_SYSTEM = """你是 CoPiano,一位温柔专业的 AI 古典钢琴老师。
回答特点:
- 简洁(每轮 ≤ 80 字)
- 鼓励优先,问题其次
- 用具体音乐术语(Baroque, 对位, legato 等)
- 中文为主,术语保留英文
- 适合学生(业余-专业过渡)
"""


@dataclass
class DialogTurn:
    """对话一轮"""
    role: str  # "user" / "assistant"
    text: str
    audio_path: Optional[str] = None
    language: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class DialogState:
    """对话状态(上下文 + 学生信息)"""
    history: list[DialogTurn] = field(default_factory=list)
    system_prompt: str = DEFAULT_LLM_PROMPT_SYSTEM
    student_name: str = "学生"
    current_piece: str = ""
    last_eval: dict = field(default_factory=dict)

    def add_user(self, text: str, language: str = None, audio_path: str = None):
        self.history.append(DialogTurn("user", text, audio_path, language))

    def add_assistant(self, text: str, audio_path: str = None):
        self.history.append(DialogTurn("assistant", text, audio_path))

    def build_messages(self, max_turns: int = 6) -> list[dict]:
        """拼 OpenAI 风格 messages,保留最近 max_turns 轮"""
        msgs = [{"role": "system", "content": self.system_prompt}]
        recent = self.history[-max_turns * 2:] if len(self.history) > max_turns * 2 else self.history
        for t in recent:
            msgs.append({"role": t.role, "content": t.text})
        return msgs


# ----- 音频 I/O -----
def record_audio(duration_s: float = 5, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """录 N 秒麦克风音频"""
    try:
        import sounddevice as sd
    except ImportError:
        print("❌ sounddevice 未装,跑: pip3 install sounddevice", file=sys.stderr)
        sys.exit(1)
    print(f"🎤 录音 {duration_s}s ...", file=sys.stderr)
    audio = sd.rec(
        int(duration_s * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    return audio.flatten()


def play_audio(audio_path: str | Path):
    """播放音频文件"""
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(str(audio_path))
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
        pygame.mixer.quit()
    except ImportError:
        # fallback:用 macOS afplay
        import subprocess
        subprocess.run(["afplay", str(audio_path)], check=True)
    except Exception as e:
        print(f"⚠️  播放失败: {e}", file=sys.stderr)


# ----- VAD(语音端点检测)-----
def detect_speech_segments(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> list[tuple[float, float]]:
    """用 Silero VAD 切分语音段,返回 [(start_s, end_s), ...]"""
    try:
        import torch
        model, utils = torch.hub.load(
            "snakers4/silero-vad",
            "silero_vad",
            force_reload=False,
            onnx=True,
        )
        get_speech_timestamps = utils[0]
    except Exception as e:
        print(f"⚠️  Silero VAD 加载失败 ({e}),使用能量阈值 fallback", file=sys.stderr)
        return _energy_vad(audio, sample_rate)

    audio_tensor = torch.from_numpy(audio).float()
    speech_timestamps = get_speech_timestamps(
        audio_tensor, model,
        sampling_rate=sample_rate,
        threshold=VAD_THRESHOLD,
        min_silence_duration_ms=VAD_MIN_SILENCE_MS,
        speech_pad_ms=VAD_SPEECH_PAD_MS,
    )
    return [(s["start"] / sample_rate, s["end"] / sample_rate) for s in speech_timestamps]


def _energy_vad(audio: np.ndarray, sample_rate: int, threshold: float = 0.01) -> list[tuple[float, float]]:
    """能量 VAD fallback"""
    frame_size = int(0.03 * sample_rate)  # 30ms
    segments = []
    in_speech = False
    start = 0
    for i in range(0, len(audio), frame_size):
        frame = audio[i:i + frame_size]
        energy = np.sqrt(np.mean(frame ** 2))
        if not in_speech and energy > threshold:
            in_speech = True
            start = i
        elif in_speech and energy < threshold:
            in_speech = False
            segments.append((start / sample_rate, i / sample_rate))
    if in_speech:
        segments.append((start / sample_rate, len(audio) / sample_rate))
    return segments


# ----- ASR -----
def transcribe_audio(audio: np.ndarray, sample_rate: int = SAMPLE_RATE, model_size: str = "small") -> dict:
    """识别音频数组,返回 {text, language, segments}"""
    import soundfile as sf
    from asr_whisper import transcribe

    # 写到临时 WAV
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
    sf.write(tmp_path, audio, sample_rate)
    try:
        return transcribe(tmp_path, model_size=model_size)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ----- LLM 推理 -----
def call_llm(messages: list[dict], backend: str = "mock", **kwargs) -> str:
    """调 LLM,返回回复文本

    backend:
    - "mock"        规则回复(测试用)
    - "mac"         Mac 本地小模型(Qwen 1.5B)
    - "gpu"         GPU 服务器 Qwen 7B(SSH)
    """
    if backend == "mock":
        return _mock_llm(messages)

    if backend == "mac":
        try:
            from llm_call_ms import call_qwen_local
            return call_qwen_local(messages, model_id="qwen/Qwen2.5-1.5B-Instruct", **kwargs)
        except Exception as e:
            print(f"⚠️  Mac LLM 失败: {e},回退到 mock", file=sys.stderr)
            return _mock_llm(messages)

    if backend == "gpu":
        try:
            from gpu_shell import run_on_gpu
            prompt_str = json.dumps(messages, ensure_ascii=False)
            result = run_on_gpu(f"python3 /root/autodl-tmp/copiano/code/scripts/llm_call.py '{prompt_str}'")
            return result.strip()
        except Exception as e:
            print(f"⚠️  GPU LLM 失败: {e},回退到 mock", file=sys.stderr)
            return _mock_llm(messages)

    return _mock_llm(messages)


def _mock_llm(messages: list[dict]) -> str:
    """Mock LLM,基于规则的简单回复(测试用)"""
    last_user = next((m for m in reversed(messages) if m["role"] == "user"), None)
    if not last_user:
        return "你好,我是 CoPiano!"

    text = last_user["content"].lower()
    if "你好" in text or "hello" in text or "hi" in text:
        return "你好!我是 CoPiano,你的 AI 钢琴老师。准备好一起练琴了吗?"
    if "评分" in text or "score" in text or "多少分" in text:
        return "你刚才那段弹得 93.5 分,有 1 个错音。重点攻小节 1 第 4 拍。"
    if "巴洛克" in text or "baroque" in text:
        return "巴洛克时期强调对位清晰度,触键颗粒分明,装饰音有规律,比如 trill 和 mordent。"
    if "怎么练" in text or "建议" in text or "practice" in text:
        return "建议先慢速 60 BPM 准后再加速,单独练错音小节 5 遍,再连贯起来。"
    if "拜厄" in text or "beyer" in text:
        return "拜厄是基础练习曲集,重点是手指独立性和节奏稳定,每首先分手练再合手。"
    return f"我听到你说:{last_user['content'][:50]}... 我会记住,继续练!"


# ----- TTS -----
async def synthesize_speech(text: str, output_path: str | Path, voice: str = None, lang: str = None) -> Path:
    """合成语音到文件"""
    from tts_edge import synthesize
    return await synthesize(text, output_path, voice=voice, lang=lang)


# ----- 主对话循环 -----
def dialog_loop(state: DialogState, llm_backend: str = "mock", voice: str = None, interactive: bool = False):
    """主对话循环

    interactive=True: 走 stdin 输入(text mode,无 mic)
    interactive=False: 一次性 --text/--listen
    """
    if interactive:
        print("🎹 CoPiano 语音陪练 (text mode,Ctrl-D 退出)")
        print(f"   LLM: {llm_backend} | 输入文字 → 我回复 → 语音播放")
        print()
        try:
            while True:
                try:
                    user_text = input("你> ").strip()
                except EOFError:
                    break
                if not user_text:
                    continue
                if user_text in ("exit", "quit", "退出"):
                    break

                state.add_user(user_text)
                msgs = state.build_messages()
                reply = call_llm(msgs, backend=llm_backend)
                state.add_assistant(reply)
                print(f"CoPiano> {reply}")

                # TTS 播放
                tmp_mp3 = Path(tempfile.mktemp(suffix=".mp3"))
                asyncio.run(synthesize_speech(reply, tmp_mp3, voice=voice))
                if tmp_mp3.exists():
                    play_audio(tmp_mp3)
                    tmp_mp3.unlink(missing_ok=True)
                print()
        except KeyboardInterrupt:
            pass
        print("\n👋 下次见!")
    else:
        # 一次性模式
        pass


def main():
    import asyncio
    parser = argparse.ArgumentParser(description="CoPiano 实时语音对话陪练")
    parser.add_argument("--text", help="直接说这段文字(跳过 ASR + LLM,只 TTS)")
    parser.add_argument("--listen", type=float, metavar="SECONDS", help="录 N 秒麦克风后对话")
    parser.add_argument("--chat", action="store_true", help="完整对话循环(text mode)")
    parser.add_argument("--demo", action="store_true", help="演示模式(Mic → ASR → TTS,无 LLM)")
    parser.add_argument("--mock-llm", action="store_true", help="用 mock LLM")
    parser.add_argument("--llm", default="mock", choices=["mock", "mac", "gpu"], help="LLM 后端")
    parser.add_argument("--voice", help="Edge-TTS 音色")
    parser.add_argument("--out", help="输出音频路径(单次模式)")
    args = parser.parse_args()

    state = DialogState()

    if args.text:
        # 单次 TTS 模式
        out_path = args.out or "/tmp/copiano_say.mp3"
        print(f"💬 {args.text}")
        asyncio.run(synthesize_speech(args.text, out_path, voice=args.voice))
        print(f"🔊 合成: {out_path}")
        play_audio(out_path)
        return

    if args.listen:
        # 单次麦克风对话
        audio = record_audio(args.listen)
        print("🔇 检测语音段 ...")
        segments = detect_speech_segments(audio)
        if not segments:
            print("⚠️  未检测到语音,试试说大声点")
            return
        for i, (start, end) in enumerate(segments):
            seg_audio = audio[int(start * SAMPLE_RATE):int(end * SAMPLE_RATE)]
            print(f"🎙️  段 {i+1}: {start:.1f}s - {end:.1f}s")
            asr_result = transcribe_audio(seg_audio)
            user_text = asr_result["text"]
            print(f"   ASR ({asr_result['language']}): {user_text}")

            state.add_user(user_text, language=asr_result["language"])
            msgs = state.build_messages()
            reply = call_llm(msgs, backend=args.llm)
            state.add_assistant(reply)
            print(f"   LLM: {reply}")

            out_path = Path(tempfile.mktemp(suffix=".mp3"))
            asyncio.run(synthesize_speech(reply, out_path, voice=args.voice))
            play_audio(out_path)
            out_path.unlink(missing_ok=True)
        return

    if args.demo:
        # 演示:录 5 秒 → ASR → TTS 回放(无 LLM)
        audio = record_audio(5)
        print("🔇 检测语音段 ...")
        segments = detect_speech_segments(audio)
        if not segments:
            print("⚠️  未检测到语音")
            return
        full_text_parts = []
        for i, (start, end) in enumerate(segments):
            seg_audio = audio[int(start * SAMPLE_RATE):int(end * SAMPLE_RATE)]
            asr_result = transcribe_audio(seg_audio)
            print(f"🎙️  段 {i+1}: {start:.1f}s - {end:.1f}s")
            print(f"   ASR: {asr_result['text']}")
            full_text_parts.append(asr_result["text"])
        full_text = " ".join(full_text_parts)
        if full_text:
            print(f"💬 识别完成: {full_text}")
            out_path = "/tmp/copiano_demo_echo.mp3"
            asyncio.run(synthesize_speech(f"我听到你说:{full_text}", out_path, voice=args.voice))
            play_audio(out_path)
        return

    if args.chat:
        # text 模式对话循环
        dialog_loop(state, llm_backend=args.llm, voice=args.voice, interactive=True)
        return

    parser.print_help()


if __name__ == "__main__":
    import asyncio
    main()
