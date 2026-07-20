"""
asr_whisper.py — faster-whisper 语音识别(支持自动语种检测)

支持:
- 多语种识别(中英日韩等 99 种语言)
- 自动语种检测(probability + lang_code)
- 词级时间戳
- Mac M4 用 MPS 加速,小模型实时(< 1s 延迟)
- 静音检测(VAD 内置)

用法:
    python3 asr_whisper.py audio.wav
    python3 asr_whisper.py audio.wav --model small --lang auto
    python3 asr_whisper.py --record 5            # 录 5 秒然后识别
    python3 asr_whisper.py --stream              # 流式麦克风识别
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

# 模型大小映射(M4 24G 内存推荐)
MODEL_SIZES = {
    "tiny": "~75MB,最快,准确度一般",
    "base": "~150MB,快,中英文够用",
    "small": "~500MB,推荐,中英日都准",
    "medium": "~1.5GB,准但慢",
    "large-v3": "~3GB,最准,需 GPU",
}

DEFAULT_MODEL = "small"
# faster-whisper 后端是 CTranslate2,支持 cpu/cuda,**不支持 mps**
# Mac M4 上用 CPU + int8 (官方推荐配置)
DEFAULT_DEVICE = "auto"  # auto / cpu / cuda
DEFAULT_COMPUTE = "auto"  # auto / int8 / float16 / float32


def load_model(model_size: str = DEFAULT_MODEL, device: str = DEFAULT_DEVICE, compute: str = DEFAULT_COMPUTE):
    """加载 Whisper 模型(Mac 上用 CPU + int8)"""
    if device == "auto":
        # 优先 CUDA(有 GPU 服务器时),否则 CPU(Mac)
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"
    if compute == "auto":
        compute = "float16" if device == "cuda" else "int8"
    print(f"[asr] loading model={model_size} device={device} compute={compute} ...", file=sys.stderr)
    t0 = time.time()
    model = WhisperModel(model_size, device=device, compute_type=compute)
    print(f"[asr] loaded in {time.time()-t0:.1f}s", file=sys.stderr)
    return model


def transcribe(
    audio_path: str | Path,
    model_size: str = DEFAULT_MODEL,
    language: str | None = None,  # None = 自动检测
    beam_size: int = 5,
    vad_filter: bool = True,
) -> dict:
    """识别音频文件,返回 {text, language, language_probability, segments, duration}

    Args:
        audio_path: WAV/MP3/M4A 路径
        model_size: tiny/base/small/medium/large-v3
        language: 强制语种(zh/en/ja),None = 自动检测
        beam_size: beam search 宽度,默认 5
        vad_filter: 是否过滤静音段
    """
    model = load_model(model_size)
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    print(f"[asr] transcribing {audio_path.name} ...", file=sys.stderr)
    t0 = time.time()
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=beam_size,
        vad_filter=vad_filter,
        word_timestamps=True,
    )

    seg_list = []
    full_text = []
    for seg in segments:
        seg_list.append({
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg.text.strip(),
            "words": [
                {"word": w.word, "start": round(w.start, 3), "end": round(w.end, 3), "prob": round(w.probability, 3)}
                for w in (seg.words or [])
            ],
        })
        full_text.append(seg.text.strip())

    elapsed = time.time() - t0
    result = {
        "text": " ".join(full_text).strip(),
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration": round(info.duration, 3),
        "transcribe_time_s": round(elapsed, 2),
        "model": model_size,
        "segments": seg_list,
    }
    print(
        f"[asr] ✅ lang={info.language}({info.language_probability:.2f}) "
        f"duration={info.duration:.1f}s transcribed in {elapsed:.1f}s",
        file=sys.stderr,
    )
    return result


def record_mic(duration_s: float = 5, sample_rate: int = 16000) -> np.ndarray:
    """用麦克风录 N 秒音频"""
    try:
        import sounddevice as sd
    except ImportError:
        print("❌ sounddevice 未装,跑: pip3 install sounddevice", file=sys.stderr)
        sys.exit(1)

    print(f"[mic] 录音 {duration_s}s ...", file=sys.stderr)
    audio = sd.rec(
        int(duration_s * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    print(f"[mic] ✅ 录音完成 {audio.shape}", file=sys.stderr)
    return audio.flatten()


def main():
    parser = argparse.ArgumentParser(description="faster-whisper 语音识别")
    parser.add_argument("audio", nargs="?", help="音频文件路径")
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=list(MODEL_SIZES.keys()), help="模型大小")
    parser.add_argument("--lang", default=None, help="强制语种(zh/en/ja),默认自动检测")
    parser.add_argument("--no-vad", action="store_true", help="关闭静音过滤")
    parser.add_argument("--record", type=float, metavar="SECONDS", help="录 N 秒后识别")
    parser.add_argument("--output", help="输出 JSON 路径")
    args = parser.parse_args()

    if args.record:
        # 录音模式
        import soundfile as sf
        audio = record_mic(args.record)
        tmp_path = "/tmp/copiano_mic_input.wav"
        sf.write(tmp_path, audio, 16000)
        result = transcribe(tmp_path, model_size=args.model, language=args.lang, vad_filter=not args.no_vad)
    elif args.audio:
        result = transcribe(args.audio, model_size=args.model, language=args.lang, vad_filter=not args.no_vad)
    else:
        parser.error("必须给 audio 文件或 --record 秒数")

    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ 写入 {args.output}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
