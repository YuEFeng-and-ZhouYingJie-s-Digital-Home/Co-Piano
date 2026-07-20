// CoPianoApp.swift — CoPiano Mac App 主入口(SwiftUI)
//
// 这是 Phase 4 的最终产物:Mac 原生 App 骨架
// 用户可在 Xcode 打开本文件 + ContentView.swift 编译运行
//
// 架构:
// - ContentView 主界面
// - RecorderView 实时录音 + 评估
// - FeedbackView LLM 反馈展示
// - HandView 视频手型预览
//
// 依赖:本机 Python 服务 (scripts/copiano.py 在 GPU 端跑)
//
// 编译要求:
// - macOS 14+
// - Xcode 15+
// - Swift 5.9+

import SwiftUI
import AVFoundation
import CoreMIDI

@main
struct CoPianoApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .frame(minWidth: 800, minHeight: 600)
        }
        .windowStyle(.titleBar)
        .commands {
            CommandMenu("CoPiano") {
                Button("Start Recording") {
                    appState.startRecording()
                }
                .keyboardShortcut("r", modifiers: [.command])

                Button("Stop Recording") {
                    appState.stopRecording()
                }
                .keyboardShortcut("r", modifiers: [.command, .shift])

                Divider()

                Button("Run Evaluation") {
                    appState.runEvaluation()
                }
                .keyboardShortcut("e", modifiers: [.command])
            }
        }
    }
}

// App 全局状态
class AppState: ObservableObject {
    @Published var isRecording = false
    @Published var currentScore: Double = 0.0
    @Published var feedbackText: String = ""
    @Published var realtimeAlert: String = ""
    @Published var pieceName: String = "Minuet in G"
    @Published var availablePieces: [String] = [
        "Minuet in G", "Sonata K.545", "Für Elise", "Nocturne Op.9", "Träumerei"
    ]

    private var recorder: AudioRecorder?
    private var evaluator: RealtimeEvaluator?

    func startRecording() {
        // TODO: 启动 MIDI 录音 + 实时评估
        isRecording = true
        realtimeAlert = "🎹 Recording started"
    }

    func stopRecording() {
        isRecording = false
        realtimeAlert = "⏸ Recording stopped"
    }

    func runEvaluation() {
        // TODO: 调用 GPU 端 copiano.py 跑端到端评估
        // 简单 demo: 模拟 5 秒后填入假数据
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            self.currentScore = 93.5
            self.feedbackText = "很好,你在整体上已经很好地掌握了大部分的音符和节奏。但在小节1中,你将第4拍弹成了3,这是一个半音的错误..."
        }
    }
}

// 主界面
struct ContentView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        NavigationSplitView {
            // 侧栏:曲目选择 + 状态
            VStack(alignment: .leading, spacing: 16) {
                Text("CoPiano")
                    .font(.largeTitle)
                    .bold()
                Text("AI 古典钢琴教练")
                    .font(.subheadline)
                    .foregroundColor(.secondary)

                Divider()

                Text("选择曲目")
                    .font(.headline)
                Picker("曲目", selection: $appState.pieceName) {
                    ForEach(appState.availablePieces, id: \.self) { piece in
                        Text(piece).tag(piece)
                    }
                }
                .pickerStyle(.menu)

                Divider()

                if appState.isRecording {
                    Label("录音中...", systemImage: "circle.fill")
                        .foregroundColor(.red)
                } else {
                    Label("就绪", systemImage: "circle")
                        .foregroundColor(.gray)
                }

                if !appState.realtimeAlert.isEmpty {
                    Text(appState.realtimeAlert)
                        .font(.caption)
                        .padding(8)
                        .background(Color.yellow.opacity(0.2))
                        .cornerRadius(6)
                }

                Spacer()

                Button(action: { appState.runEvaluation() }) {
                    Label("运行评估", systemImage: "play.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
            }
            .padding()
            .frame(minWidth: 200)
        } detail: {
            // 主区:评估 + 反馈
            EvaluationView()
        }
    }
}

// 评估主视图
struct EvaluationView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            // 评分大圆
            HStack {
                Spacer()
                ZStack {
                    Circle()
                        .stroke(Color.gray.opacity(0.2), lineWidth: 12)
                    Circle()
                        .trim(from: 0, to: appState.currentScore / 100)
                        .stroke(scoreColor, style: StrokeStyle(lineWidth: 12, lineCap: .round))
                        .rotationEffect(.degrees(-90))
                        .animation(.easeInOut, value: appState.currentScore)
                    VStack {
                        Text(String(format: "%.1f", appState.currentScore))
                            .font(.system(size: 48, weight: .bold))
                        Text("/ 100")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                }
                .frame(width: 200, height: 200)
                Spacer()
            }
            .padding(.top, 30)

            // 反馈文本
            if !appState.feedbackText.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("AI 老师反馈")
                        .font(.headline)
                    ScrollView {
                        Text(appState.feedbackText)
                            .padding()
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .background(Color.gray.opacity(0.1))
                    .cornerRadius(8)
                }
            }

            // 录音控制
            HStack {
                Button(action: {
                    if appState.isRecording {
                        appState.stopRecording()
                    } else {
                        appState.startRecording()
                    }
                }) {
                    Label(
                        appState.isRecording ? "停止" : "开始录音",
                        systemImage: appState.isRecording ? "stop.fill" : "record.circle"
                    )
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .tint(appState.isRecording ? .red : .blue)
            }
            .padding(.top, 10)

            Spacer()
        }
        .padding()
    }

    var scoreColor: Color {
        if appState.currentScore >= 90 { return .green }
        if appState.currentScore >= 70 { return .yellow }
        return .red
    }
}

// 音频录制(占位)
class AudioRecorder: ObservableObject {
    @Published var isRecording = false
    @Published var level: Double = 0.0

    func start() {
        // TODO: 用 AVAudioEngine 录音
        isRecording = true
    }

    func stop() -> URL? {
        isRecording = false
        // TODO: 返回 MIDI 文件 URL
        return nil
    }
}

// 实时评估(占位)
class RealtimeEvaluator: ObservableObject {
    @Published var alert: String = ""

    func start() {
        // TODO: 调用 real_time_feedback.py
    }

    func stop() {
        // TODO: 停止评估
    }
}
