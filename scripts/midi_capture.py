"""
midi_capture.py — Mac 端 MIDI 实时采集(基于 python-rtmidi + mido)

两种模式:
1. list: 列出所有 MIDI 设备
2. record: 录音到 MIDI 文件(按 Ctrl+C 停止)
3. watch: 实时打印按键事件(测试用)

用法:
    python3 midi_capture.py list
    python3 midi_capture.py record output.mid [device_name_substr]
    python3 midi_capture.py watch [device_name_substr]
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import mido
import rtmidi


def list_devices() -> list[dict]:
    """列出所有 MIDI 输入/输出设备"""
    out = {"inputs": [], "outputs": []}
    m = rtmidi.MidiIn()
    for i in range(m.get_port_count()):
        out["inputs"].append({"index": i, "name": m.get_port_name(i)})
    m2 = rtmidi.MidiOut()
    for i in range(m2.get_port_count()):
        out["outputs"].append({"index": i, "name": m2.get_port_name(i)})
    return out


def find_device(substr: str = "", kind: str = "input") -> int:
    """找包含 substr 的设备,返回 index;找不到抛错"""
    if kind == "input":
        m = rtmidi.MidiIn()
        names = [m.get_port_name(i) for i in range(m.get_port_count())]
    else:
        m = rtmidi.MidiOut()
        names = [m.get_port_name(i) for i in range(m.get_port_count())]
    if not substr:
        if not names:
            raise RuntimeError(f"没有 MIDI {kind} 设备")
        return 0
    for i, n in enumerate(names):
        if substr.lower() in n.lower():
            return i
    raise RuntimeError(f"找不到包含 '{substr}' 的 {kind} 设备;现有: {names}")


def record(out_path: str, device_substr: str = "") -> int:
    """录音到 MIDI 文件(按 Ctrl+C 停止)"""
    dev_idx = find_device(device_substr, "input")
    print(f"[record] 设备 idx={dev_idx}, 输出={out_path}")
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=500000, time=0))

    port = mido.open_input(dev_idx)
    print("[record] 开始录音,按 Ctrl+C 停止...")
    start = time.time()
    n_events = 0
    try:
        for msg in port:
            t = time.time() - start
            track.append(msg.copy(time=int(t * 1000)))
            n_events += 1
            if n_events % 100 == 0:
                print(f"  [{t:.1f}s] {n_events} events", end="\r")
    except KeyboardInterrupt:
        print(f"\n[record] 停止,共 {n_events} events, {time.time()-start:.1f}s")
    finally:
        port.close()

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    mid.save(out_path)
    print(f"[record] 保存到 {out_path} ({Path(out_path).stat().st_size / 1024:.1f} KB)")
    return 0


def watch(device_substr: str = "") -> int:
    """实时打印按键事件"""
    dev_idx = find_device(device_substr, "input")
    print(f"[watch] 设备 idx={dev_idx},实时显示事件(按 Ctrl+C 停止)")
    port = mido.open_input(dev_idx)
    try:
        for msg in port:
            t = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            if msg.type == "note_on" and msg.velocity > 0:
                note_name = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][msg.note % 12]
                octave = msg.note // 12 - 1
                print(f"  {t}  ON  {note_name}{octave} (MIDI {msg.note})  vel={msg.velocity}")
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                note_name = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][msg.note % 12]
                octave = msg.note // 12 - 1
                print(f"  {t}  OFF {note_name}{octave} (MIDI {msg.note})")
            else:
                print(f"  {t}  {msg}")
    except KeyboardInterrupt:
        print("\n[watch] 停止")
    finally:
        port.close()
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    p_rec = sub.add_parser("record")
    p_rec.add_argument("out")
    p_rec.add_argument("device", nargs="?", default="")
    p_watch = sub.add_parser("watch")
    p_watch.add_argument("device", nargs="?", default="")
    args = ap.parse_args()

    if args.cmd == "list":
        d = list_devices()
        print(f"MIDI inputs ({len(d['inputs'])}):")
        for x in d["inputs"]:
            print(f"  [{x['index']}] {x['name']}")
        print(f"MIDI outputs ({len(d['outputs'])}):")
        for x in d["outputs"]:
            print(f"  [{x['index']}] {x['name']}")
        if not d["inputs"] and not d["outputs"]:
            print("  (无 MIDI 设备)")
            print("  提示:用 USB-MIDI 转换器连接钢琴键盘,或用 'IAC Driver' 创建虚拟设备")
    elif args.cmd == "record":
        return record(args.out, args.device)
    elif args.cmd == "watch":
        return watch(args.device)


if __name__ == "__main__":
    sys.exit(main() or 0)
