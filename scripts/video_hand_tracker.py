"""
video_hand_tracker.py — 视频手型追踪(MediaPipe Hands 占位骨架)

Phase 4 完整方案:
- 摄像头视频流(OpenCV)
- 每帧检测手部关键点(21 个)
- 提取手指角度 / 关节位置
- 配合 MIDI 评估给"手型是否正确"反馈

依赖问题:
- mediapipe Python 包(2026)安装慢/失败
- MediaPipe Tasks API 模型 (~6MB)需下载

本脚本处理:
- OpenCV 视频流(已可用)
- Hand landmarker 占位(若 mediapipe 不可用)
- 完整架构设计(用户装好 mediapipe 后即用)

用法:
    python3 video_hand_tracker.py              # 默认摄像头
    python3 video_hand_tracker.py video.mp4   # 视频文件
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

# OpenCV 必有(cv2 已装)
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

# MediaPipe 可选
HAS_MEDIAPIPE = False
try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    HAS_MEDIAPIPE = True
except ImportError:
    pass


# Hand landmark 索引(21 个关键点)
HAND_LANDMARKS = {
    0: "wrist",
    1: "thumb_cmc", 2: "thumb_mcp", 3: "thumb_ip", 4: "thumb_tip",
    5: "index_mcp", 6: "index_pip", 7: "index_dip", 8: "index_tip",
    9: "middle_mcp", 10: "middle_pip", 11: "middle_dip", 12: "middle_tip",
    13: "ring_mcp", 14: "ring_pip", 15: "ring_dip", 16: "ring_tip",
    17: "pinky_mcp", 18: "pinky_pip", 19: "pinky_dip", 20: "pinky_tip",
}


def get_hand_landmarks_opencv(frame):
    """占位:用 OpenCV 简单肤色检测(无 mediapipe 时 fallback)
    Returns: [(x, y, name)] 列表
    """
    # 简单肤色检测(YCrCb 空间)
    ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    mask = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
    # 找轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return []
    # 最大轮廓(假设是手)
    cnt = max(contours, key=cv2.contourArea)
    if cv2.contourArea(cnt) < 5000:
        return []
    # 返回中心 + 几个近似关键点
    M = cv2.moments(cnt)
    if M["m00"] == 0:
        return []
    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    return [(cx, cy, "hand_center")]


def get_hand_landmarks_mediapipe(frame_bgr, detector):
    """用 MediaPipe HandLandmarker 检 21 个关键点
    Returns: [(x, y, name)] 列表
    """
    import mediapipe as mp
    import numpy as np
    # 转 RGB
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
    # 检
    result = detector.detect(image)
    out = []
    if result.hand_landmarks:
        for hand_landmarks in result.hand_landmarks:
            for idx, lm in enumerate(hand_landmarks):
                x = int(lm.x * frame_bgr.shape[1])
                y = int(lm.y * frame_bgr.shape[0])
                name = HAND_LANDMARKS.get(idx, f"pt_{idx}")
                out.append((x, y, name))
    return out


def analyze_hand_pose(landmarks: list) -> dict:
    """简单手型分析(从 landmarks 提取)
    提取:
    - 手腕位置
    - 5 指指尖是否伸展(每指 0-1)
    - 整体手型姿态(relaxed / tense / unknown)
    """
    if not landmarks:
        return {"pose": "unknown", "fingers": [0, 0, 0, 0, 0]}
    lm_dict = {name: (x, y) for x, y, name in landmarks}
    if "wrist" not in lm_dict:
        return {"pose": "unknown", "fingers": [0, 0, 0, 0, 0]}
    wx, wy = lm_dict["wrist"]
    fingers = []
    for tip_name, base_name in [
        ("thumb_tip", "thumb_mcp"),
        ("index_tip", "index_mcp"),
        ("middle_tip", "middle_mcp"),
        ("ring_tip", "ring_mcp"),
        ("pinky_tip", "pinky_mcp"),
    ]:
        if tip_name in lm_dict and base_name in lm_dict:
            tx, ty = lm_dict[tip_name]
            bx, by = lm_dict[base_name]
            # 指尖离手腕比基部远 → 伸展
            tip_dist = ((tx - wx) ** 2 + (ty - wy) ** 2) ** 0.5
            base_dist = ((bx - wx) ** 2 + (by - wy) ** 2) ** 0.5
            ratio = tip_dist / max(1, base_dist)
            fingers.append(1.0 if ratio > 1.5 else 0.0)
        else:
            fingers.append(0.0)
    pose = "relaxed" if sum(fingers) < 2 else ("tense" if sum(fingers) > 4 else "neutral")
    return {"pose": pose, "fingers": fingers, "wrist": (wx, wy)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?", default="0", help="视频源(数字=camera 索引, 或视频文件路径)")
    ap.add_argument("--output", default=None, help="输出视频(可选)")
    ap.add_argument("--display", action="store_true", help="显示窗口")
    args = ap.parse_args()

    if not HAS_CV2:
        print("❌ 需要 OpenCV: pip install opencv-python")
        return 1

    # 视频源
    src = int(args.input) if args.input.isdigit() else args.input
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        print(f"❌ 无法打开视频源: {src}")
        return 1
    print(f"[video] 打开: {src} ({int(cap.get(cv2.CAP_PROP_FPS))} fps)")

    # MediaPipe HandLandmarker(若可用)
    detector = None
    if HAS_MEDIAPIPE:
        try:
            model_path = Path.home() / ".cache" / "mediapipe" / "hand_landmarker.task"
            if not model_path.exists():
                print(f"  [warn] HandLandmarker 模型未下载: {model_path}")
                print(f"         下载: curl -L https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task -o {model_path}")
            else:
                base_options = python.BaseOptions(model_asset_path=str(model_path))
                options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=2)
                detector = vision.HandLandmarker.create_from_options(options)
                print(f"  [ok] MediaPipe HandLandmarker 加载完成")
        except Exception as e:
            print(f"  [warn] MediaPipe 加载失败: {e}")

    # 输出视频(可选)
    writer = None
    if args.output:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        writer = cv2.VideoWriter(args.output, fourcc, fps, (w, h))
        print(f"[video] 输出到: {args.output}")

    print("[video] 按 q 退出(若 --display)")

    n_frames = 0
    t0 = time.time()
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        n_frames += 1
        # 检测手部
        if detector:
            landmarks = get_hand_landmarks_mediapipe(frame, detector)
        else:
            landmarks = get_hand_landmarks_opencv(frame)
        # 画
        for x, y, name in landmarks:
            color = (0, 255, 0) if "tip" in name else (255, 0, 0)
            cv2.circle(frame, (x, y), 4, color, -1)
        # 分析手型
        pose = analyze_hand_pose(landmarks)
        if "wrist" in pose:
            cv2.putText(frame, f"pose={pose['pose']} fingers={sum(pose['fingers']):.0f}/5",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        # 显示
        if args.display:
            cv2.imshow("CoPiano Hand Tracker", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        # 输出
        if writer:
            writer.write(frame)
        # 进度
        if n_frames % 30 == 0:
            elapsed = time.time() - t0
            fps_real = n_frames / max(0.1, elapsed)
            print(f"  frame {n_frames}: {fps_real:.1f} fps, {len(landmarks)} landmarks")

    cap.release()
    if writer:
        writer.release()
    print(f"\n[video] 完成: {n_frames} 帧,{time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
