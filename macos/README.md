# CoPiano Mac App

SwiftUI 源码,可在 Xcode 编译运行。

## 编译要求

- macOS 14+ (Sonoma)
- Xcode 15+
- Swift 5.9+
- 推荐:Apple Silicon (M1/M2/M3/M4)

## 编译步骤

1. **打开 Xcode** → File → New → Project → macOS App
2. **命名**:CoPiano(或其他)
3. **替换** 自动生成的 `ContentView.swift` 和 `CoPianoApp.swift` 为本目录文件
4. **Bundle ID**:com.copiano.app(或自定义)
5. **Capabilities**:
   - 勾选 Microphone(录音)
   - 勾选 Camera(若用视频手型)
6. **Build & Run** (⌘R)

## 架构

```
CoPianoApp (主入口)
├── AppState (全局状态)
├── ContentView (主界面)
│   ├── 侧栏(曲目选择 + 录音状态)
│   └── 详情(评分大圆 + 反馈)
└── (待集成)
    ├── AudioRecorder (AVAudioEngine + CoreMIDI)
    ├── RealtimeEvaluator (调 real_time_feedback.py)
    └── HandTracker (AVCaptureSession + MediaPipe)
```

## 与 Python 后端集成

Mac App 调用 GPU 端 `copiano.py` 通过 HTTP 或 SSH:

```swift
// TODO: 用 URLSession 或 Process 调
let task = Process()
task.launchPath = "/usr/bin/ssh"
task.arguments = ["user@gpu-server", "python3 copiano.py ..."]
```

## 当前状态(占位)

- ✅ SwiftUI 骨架(评分圆 + 反馈区 + 录音按钮)
- ❌ 真实录音(AVAudioEngine)
- ❌ 真实评估(集成 real_time_feedback.py)
- ❌ 真实手型(集成 video_hand_tracker.py)
- ❌ 真实 LLM 反馈(调 GPU 端)

## 已知限制

- 占位状态:录音/评估/手型都是 fake
- 需 macOS 14+ 和 Xcode 15+
- 用户需有 GPU 端服务器在跑 copiano.py

## 下一步

1. 集成 AVAudioEngine 真实录音
2. 集成 real_time_feedback.py 通过 HTTP
3. 集成 video_hand_tracker.py
4. 实现 LLM 反馈流式显示
5. 提交 Mac App Store(可选)
