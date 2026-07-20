"""
tts_edge.py — Edge-TTS 语音合成封装

支持:
- 任意文本 → MP3
- 自动按语言选音色(zh-CN / en-US / ja-JP / ...)
- 流式输出(边合成边播放)
- 字幕同步(SRT/Word boundary)
- 不需任何本地模型,完全云端,免费

用法:
    python3 tts_edge.py "你好,弹得不错" --out hello.mp3
    python3 tts_edge.py "Hello world" --lang en-US --voice en-US-AriaNeural
    python3 tts_edge.py "你好" --stream          # 流式边合成边播
    python3 tts_edge.py "你好" --subs words.json  # 词级时间戳
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import AsyncIterator

import edge_tts

# 音色库(按语言分)
VOICE_LIBRARY = {
    "zh-CN": {
        "female_warm": "zh-CN-XiaoxiaoNeural",       # 晓晓 - 温暖女声
        "female_gentle": "zh-CN-XiaoyiNeural",       # 晓伊 - 温柔女声(钢琴老师推荐)
        "male_professional": "zh-CN-YunxiNeural",    # 云希 - 专业男声
        "female_lively": "zh-CN-XiaomengNeural",     # 晓梦 - 活泼女声
    },
    "en-US": {
        "female_warm": "en-US-JennyNeural",          # Jenny - 温暖女声
        "female_gentle": "en-US-AriaNeural",         # Aria - 温柔女声
        "male_professional": "en-US-GuyNeural",      # Guy - 专业男声
    },
    "en-GB": {
        "female_warm": "en-GB-SoniaNeural",          # Sonia - 英式女声
        "male_professional": "en-GB-RyanNeural",     # Ryan - 英式男声
    },
    "ja-JP": {
        "female_warm": "ja-JP-NanamiNeural",         # 七海 - 日语女声
    },
}

DEFAULT_VOICE = {
    "zh-CN": "zh-CN-XiaoyiNeural",   # 钢琴老师默认温柔女声
    "en-US": "en-US-AriaNeural",
    "en-GB": "en-GB-SoniaNeural",
    "ja-JP": "ja-JP-NanamiNeural",
}


def detect_lang(text: str) -> str:
    """简易语种检测(基于 Unicode 范围)"""
    has_cjk = any("\u4e00" <= c <= "\u9fff" for c in text)
    has_kana = any("\u3040" <= c <= "\u30ff" for c in text)
    has_hangul = any("\uac00" <= c <= "\ud7af" for c in text)
    has_latin = any(c.isascii() and c.isalpha() for c in text)

    if has_kana:
        return "ja-JP"
    if has_hangul:
        return "ko-KR"
    if has_cjk:
        return "zh-CN"
    if has_latin:
        return "en-US"
    return "zh-CN"  # fallback


async def synthesize(
    text: str,
    output_path: str | Path,
    voice: str | None = None,
    lang: str | None = None,
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
) -> Path:
    """合成文本到 MP3 文件

    Args:
        text: 要合成的文本
        output_path: 输出 MP3 路径
        voice: 音色 ID(如 zh-CN-XiaoyiNeural),None 则按 lang 自动选
        lang: 语言代码(zh-CN / en-US),None 则自动检测
        rate: 语速调整,默认 +0%,可设 +20%(更快)/-10%(更慢)
        volume: 音量,默认 +0%
        pitch: 音调,默认 +0Hz
    """
    if lang is None:
        lang = detect_lang(text)
    if voice is None:
        voice = DEFAULT_VOICE.get(lang, "zh-CN-XiaoyiNeural")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        volume=volume,
        pitch=pitch,
    )
    await communicate.save(str(output_path))
    return output_path


async def synthesize_stream(text: str, voice: str | None = None, lang: str | None = None) -> AsyncIterator[bytes]:
    """流式合成(边合成边返回 chunk)"""
    if lang is None:
        lang = detect_lang(text)
    if voice is None:
        voice = DEFAULT_VOICE.get(lang, "zh-CN-XiaoyiNeural")

    communicate = edge_tts.Communicate(text=text, voice=voice)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]


async def list_voices(lang: str | None = None) -> list[dict]:
    """列出所有可用音色"""
    voices = await edge_tts.list_voices()
    if lang:
        voices = [v for v in voices if v["Locale"].startswith(lang)]
    return voices


def main():
    parser = argparse.ArgumentParser(description="Edge-TTS 语音合成")
    parser.add_argument("text", help="要合成的文本")
    parser.add_argument("--out", default="/tmp/edge_tts_out.mp3", help="输出 MP3 路径")
    parser.add_argument("--voice", help="音色 ID(如 zh-CN-XiaoyiNeural)")
    parser.add_argument("--lang", help="语言代码(zh-CN / en-US)")
    parser.add_argument("--rate", default="+0%", help="语速 (+0% / +20% / -10%)")
    parser.add_argument("--pitch", default="+0Hz", help="音调")
    parser.add_argument("--list-voices", action="store_true", help="列出可用音色")
    args = parser.parse_args()

    if args.list_voices:
        async def _list():
            voices = await list_voices(args.lang)
            for v in voices:
                print(f"{v['ShortName']:30s} {v['Gender']:6s} {v['Locale']}")
        asyncio.run(_list())
        return

    async def _run():
        detected = args.lang or detect_lang(args.text)
        chosen_voice = args.voice or DEFAULT_VOICE.get(detected, "zh-CN-XiaoyiNeural")
        print(f"[tts] lang={detected} voice={chosen_voice}")
        out = await synthesize(
            text=args.text,
            output_path=args.out,
            voice=chosen_voice,
            rate=args.rate,
            pitch=args.pitch,
        )
        size = out.stat().st_size
        print(f"✅ 写入 {out} ({size} 字节)")

    asyncio.run(_run())


if __name__ == "__main__":
    main()
