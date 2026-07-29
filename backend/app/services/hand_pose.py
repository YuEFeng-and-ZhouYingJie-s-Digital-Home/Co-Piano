"""
hand_pose_analyzer.py — 钢琴手型 9 维度分析器

Cycle 4 Stage 2 实现:
- 输入: MediaPipe 21 关键点 / OpenCV 估算 / 合成 JSON
- 9 维度评分 + 0-100 综合分
- 教学建议生成 (基于弱维度)
- voice_dialog 集成

9 维度:
1. wrist_height (手腕高度)
2. hand_arch (手弓)
3. finger_curl (5 指弯曲度)
4. thumb_position (拇指位置)
5. palm_contact (手掌接触)
6. hand_rotation (手部旋转)
7. symmetry_LR (左右手对称)
8. finger_independence (4/5 指独立性)
9. relaxation (放松度)
"""

import json
import math
import sys

# === MediaPipe 21 关键点索引 ===
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20


# === 数学工具函数 ===

def vec3(a, b) -> tuple[float, float, float]:
    """向量 b - a (允许输入 list/dict)"""
    return (b[0] - a[0], b[1] - a[1], b[2] - a[2])


def vec_len(v) -> float:
    return math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)


def vec2_angle_deg(v1, v2) -> float:
    """2D 向量夹角 (度)"""
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    n1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
    n2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2)
    if n1 < 1e-9 or n2 < 1e-9:
        return 0.0
    cos_a = max(-1.0, min(1.0, dot / (n1 * n2)))
    return math.degrees(math.acos(cos_a))


def get_point(landmarks, idx) -> tuple[float, float, float]:
    """从 21 关键点 list 中取一个点"""
    p = landmarks[idx]
    if isinstance(p, dict):
        return (p.get('x', 0), p.get('y', 0), p.get('z', 0))
    return (p[0], p[1], p[2] if len(p) > 2 else 0)


def get_xy(landmarks, idx) -> tuple[float, float]:
    p = get_point(landmarks, idx)
    return (p[0], p[1])


# === 9 维度计算 ===

def compute_wrist_height(landmarks) -> float:
    """
    维度 1: 手腕高度
    手腕 Y 坐标 vs 指尖 Y 坐标的相对位置
    理想: 手腕与指尖接近(手腕不太高也不太低)
    分数: 0-100
    """
    wrist = get_xy(landmarks, WRIST)
    index_tip = get_xy(landmarks, INDEX_TIP)
    middle_tip = get_xy(landmarks, MIDDLE_TIP)
    # 取指尖平均
    tips_y = (index_tip[1] + middle_tip[1]) / 2
    # 屏幕坐标 Y 向下为正,手腕比指尖高(Y 更小)为放松
    diff = wrist[1] - tips_y  # 正数 = 手腕在指尖上方(高于指尖)
    # 理想 diff: 0.0-0.05(归一化坐标),太高紧绷,太低塌陷
    # 假设手部坐标归一化到 0-1
    if diff < -0.05:  # 手腕低于指尖
        return max(0, 50 + diff * 1000)  # 塌陷
    if diff > 0.15:  # 手腕过高
        return max(0, 100 - (diff - 0.15) * 500)
    return 90  # 理想范围


def compute_hand_arch(landmarks) -> float:
    """
    维度 2: 手弓弯曲度
    MCP-PIP-TIP 三点形成的曲率
    理想: 中等弯曲 (~0.6-0.8)
    """
    # 用食指 PIP 到 WRIST 的距离 / MCP 到 WRIST 距离 之比
    wrist = get_xy(landmarks, WRIST)
    index_mcp = get_xy(landmarks, INDEX_MCP)
    index_pip = get_xy(landmarks, INDEX_PIP)
    middle_pip = get_xy(landmarks, MIDDLE_PIP)
    ring_pip = get_xy(landmarks, RING_PIP)
    pinky_pip = get_xy(landmarks, PINKY_PIP)

    # 手弓顶部 (4 指 PIP 平均)
    arch_y = (index_pip[1] + middle_pip[1] + ring_pip[1] + pinky_pip[1]) / 4
    # 手腕-MCP 基线
    base_y = (wrist[1] + index_mcp[1]) / 2
    # 弯曲度: PIP 离基线多远
    arch_height = abs(base_y - arch_y)

    # 假设手宽 0.15 (归一化),理想 arch_height = 0.04-0.08
    if arch_height < 0.02:
        return 40  # 太平,无手弓
    if arch_height < 0.04:
        return 70  # 弱手弓
    if arch_height <= 0.08:
        return 95  # 理想
    if arch_height <= 0.12:
        return 75  # 略深
    return 50  # 过度


def compute_finger_curl(landmarks) -> dict[str, float]:
    """
    维度 3: 5 指弯曲度
    每指 MCP-PIP-TIP 形成的角度
    理想: 60-100° (放松弯曲)
    """
    finger_joints = {
        'thumb': (THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP),
        'index': (INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP),
        'middle': (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP),
        'ring': (RING_MCP, RING_PIP, RING_DIP, RING_TIP),
        'pinky': (PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP),
    }
    result = {}
    for name, (mcp, pip, dip, tip) in finger_joints.items():
        try:
            mcp_xy = get_xy(landmarks, mcp)
            pip_xy = get_xy(landmarks, pip)
            tip_xy = get_xy(landmarks, tip)
            v1 = (pip_xy[0] - mcp_xy[0], pip_xy[1] - mcp_xy[1])
            v2 = (tip_xy[0] - pip_xy[0], tip_xy[1] - pip_xy[1])
            angle = vec2_angle_deg(v1, v2)
            # 弯曲度评分: 理想 60-100°,直线 180°,完全弯曲 ~30°
            if 50 <= angle <= 110:
                score = 95
            elif 30 <= angle < 50:
                score = 75  # 略弯
            elif 110 < angle <= 150:
                score = 70  # 略直
            elif angle > 150:
                score = 50  # 太直
            else:
                score = 55  # 太弯
            result[name] = {'angle': round(angle, 1), 'score': score}
        except Exception:
            result[name] = {'angle': 0, 'score': 50}
    return result


def compute_thumb_position(landmarks) -> float:
    """
    维度 4: 拇指位置
    拇指 MCP 到 INDEX_MCP 的方向
    理想: 拇指外展,~30-60° 偏离食指
    """
    thumb_mcp = get_xy(landmarks, THUMB_MCP)
    thumb_tip = get_xy(landmarks, THUMB_TIP)
    index_mcp = get_xy(landmarks, INDEX_MCP)
    wrist = get_xy(landmarks, WRIST)
    # 拇指向量 (MCP → TIP)
    thumb_vec = (thumb_tip[0] - thumb_mcp[0], thumb_tip[1] - thumb_mcp[1])
    # 手掌向量 (WRIST → INDEX_MCP)
    palm_vec = (index_mcp[0] - wrist[0], index_mcp[1] - wrist[1])
    # 2D 角度
    angle = vec2_angle_deg(thumb_vec, palm_vec)
    # 理想: 30-70°
    if 30 <= angle <= 70:
        return 90
    if 20 <= angle < 30 or 70 < angle <= 90:
        return 70
    if angle < 20:
        return 40  # 拇指太内收
    return 50  # 拇指太外展


def compute_palm_contact(landmarks) -> float:
    """
    维度 5: 手掌接触
    4 指 MCP 与 WRIST 的 Y 距离 → 估计手掌"摊开"程度
    理想: 4 MCP 略低于 WRIST(手掌自然拱起)
    """
    wrist = get_xy(landmarks, WRIST)
    mcps = [INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP]
    mcp_ys = [get_xy(landmarks, m)[1] for m in mcps]
    avg_mcp_y = sum(mcp_ys) / 4
    # 4 个 MCP 应在 WRIST 略上方(Y 略小)
    diff = wrist[1] - avg_mcp_y  # 正数 = MCP 在手腕上方
    if 0.02 <= diff <= 0.10:
        return 90  # 理想
    if diff < 0.02:
        return 60  # 手掌太直
    if diff <= 0.15:
        return 75  # 略拱
    return 50  # 过度拱


def compute_hand_rotation(landmarks) -> float:
    """
    维度 6: 手部旋转
    用 4 指 TIP 的 X 坐标分布
    理想: 4 指 tip 大致在同一 X 平面(手没内/外翻)
    """
    tips_x = [get_xy(landmarks, m)[0] for m in [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]]
    # 标准差
    mean_x = sum(tips_x) / 4
    variance = sum((x - mean_x) ** 2 for x in tips_x) / 4
    std = math.sqrt(variance)
    # 理想 std < 0.01 (很平)
    if std < 0.01:
        return 95
    if std < 0.02:
        return 80
    if std < 0.04:
        return 60
    return 40  # 手部明显旋转


def compute_symmetry(left_lm, right_lm) -> float:
    """
    维度 7: 左右手对称
    比较两手 finger_curl 平均
    """
    if not left_lm or not right_lm:
        return 75  # 单手数据,默认中等分
    lc = compute_finger_curl(left_lm)
    rc = compute_finger_curl(right_lm)
    fingers = ['index', 'middle', 'ring', 'pinky']
    diffs = []
    for f in fingers:
        if f in lc and f in rc:
            diffs.append(abs(lc[f]['angle'] - rc[f]['angle']))
    if not diffs:
        return 75
    avg_diff = sum(diffs) / len(diffs)
    if avg_diff < 10:
        return 95
    if avg_diff < 20:
        return 80
    if avg_diff < 35:
        return 60
    return 40


def compute_finger_independence(landmarks) -> float:
    """
    维度 8: 4/5 指独立性
    无名指/小指 vs 食指/中指 的弯曲差
    理想: 差异小(独立性高)
    """
    fc = compute_finger_curl(landmarks)
    strong = (fc['index']['angle'] + fc['middle']['angle']) / 2
    weak = (fc['ring']['angle'] + fc['pinky']['angle']) / 2
    diff = abs(strong - weak)
    if diff < 10:
        return 90
    if diff < 25:
        return 75
    if diff < 45:
        return 55
    return 35  # 4/5 指明显弱


def compute_relaxation(landmarks) -> float:
    """
    维度 9: 放松度
    估算: 5 指平均弯曲度
    理想: 平均 60-100°(放松弯曲),过直或过弯都紧张
    """
    fc = compute_finger_curl(landmarks)
    angles = [fc[f]['angle'] for f in ['index', 'middle', 'ring', 'pinky']]
    avg = sum(angles) / 4
    if 60 <= avg <= 110:
        return 95
    if 40 <= avg < 60 or 110 < avg <= 140:
        return 75
    if avg < 40:
        return 50  # 过度握紧
    return 50  # 过度伸直


# === 综合分析 ===

def analyze_hand_pose(landmarks, left_landmarks=None, right_landmarks=None) -> dict:
    """
    完整 9 维度手型分析
    返回: dict with 9 dims + overall + suggestions
    """
    wrist_h = compute_wrist_height(landmarks)
    arch = compute_hand_arch(landmarks)
    finger_curl = compute_finger_curl(landmarks)
    thumb = compute_thumb_position(landmarks)
    palm = compute_palm_contact(landmarks)
    rotation = compute_hand_rotation(landmarks)
    sym = compute_symmetry(left_landmarks, right_landmarks)
    indep = compute_finger_independence(landmarks)
    relax = compute_relaxation(landmarks)

    # curl 平均分
    curl_scores = [v['score'] for v in finger_curl.values()]
    curl_avg = sum(curl_scores) / len(curl_scores) if curl_scores else 60

    # 综合分加权
    weights = {
        'wrist_height': 0.10,
        'hand_arch': 0.20,
        'finger_curl': 0.20,
        'thumb_position': 0.15,
        'palm_contact': 0.10,
        'hand_rotation': 0.05,
        'symmetry': 0.05,
        'finger_independence': 0.10,
        'relaxation': 0.05,
    }
    dims = {
        'wrist_height': wrist_h,
        'hand_arch': arch,
        'finger_curl': curl_avg,
        'thumb_position': thumb,
        'palm_contact': palm,
        'hand_rotation': rotation,
        'symmetry': sym,
        'finger_independence': indep,
        'relaxation': relax,
    }
    overall = sum(dims[k] * weights[k] for k in weights)

    # 教学建议 (按最弱 3 维度)
    sorted_dims = sorted(dims.items(), key=lambda x: x[1])
    suggestions = []
    advice_map = {
        'wrist_height': '手腕位置需调整:理想状态手腕与指尖接近,练习 "weight technique" 让手臂自然重力',
        'hand_arch': '手弓需要建立:4 指 PIP 应在 MCP 之上形成拱形,推荐 Pianimals 抓握练习',
        'finger_curl': '指节弯曲度需优化:每指 60-100° 弯曲,避免全直或全弯',
        'thumb_position': '拇指位置需调整:外展 30-70° 最佳,避免压在食指下',
        'palm_contact': '手掌接触不够:让掌心靠近琴键,改善触感反馈',
        'hand_rotation': '手部有内外翻:保持 4 指指尖在同一平面,想象"握鸡蛋"',
        'symmetry': '左右手不对称:双手镜像练习 (慢速 60 BPM 各 30 次)',
        'finger_independence': '4/5 指独立性弱:无名指小指弯曲度不够,推荐 Hanon 练习第 1-20 条',
        'relaxation': '手部紧张:平均弯曲度偏离 60-110° 区间,练 "piano massage" 5 分钟',
    }
    for dim_name, score in sorted_dims[:3]:
        if score < 80:
            suggestions.append({
                'dimension': dim_name,
                'score': round(score, 1),
                'advice': advice_map[dim_name],
                'severity': 'high' if score < 60 else 'medium',
            })

    return {
        'dimensions': {k: round(v, 1) for k, v in dims.items()},
        'finger_details': {k: v for k, v in finger_curl.items()},
        'overall_score': round(overall, 1),
        'weights': weights,
        'suggestions': suggestions,
        'grade': _score_to_grade(overall),
    }


def _score_to_grade(score) -> str:
    if score >= 90: return '优秀 (Excellent)'
    if score >= 80: return '良好 (Good)'
    if score >= 70: return '中等 (Average)'
    if score >= 60: return '及格 (Pass)'
    return '需改进 (Need Work)'


# === 合成测试数据生成器 ===

def generate_test_hand_pose(pose_type: str = 'perfect') -> list[list[float]]:
    """
    生成 21 关键点合成数据用于测试
    pose_type: perfect / tense / collapsed / asymmetric
    真实手型:指关节要形成"鸟嘴"形弯曲 ~70-90°
    """
    # 设计思路:让每指的 MCP-PIP-TIP 形成约 75-85° 角 (理想)
    # MCP-PIP 向量: (dx_pip, dy_pip), TIP 在 PIP 偏"内侧"位置
    # 形成 80° curl 角: TIP - PIP 与 PIP - MCP 的点积 = |v1||v2| * cos(80°) ≈ 0.174

    # WRIST 在 (0.50, 0.65) - 与 MCP 同一水平(理想)
    base = [
        [0.50, 0.65, 0],  # 0 WRIST
        # 拇指:从手腕斜向外
        [0.40, 0.62, 0],  # 1 THUMB_CMC
        [0.35, 0.58, 0],  # 2 THUMB_MCP
        [0.33, 0.54, 0],  # 3 THUMB_IP
        [0.32, 0.50, 0],  # 4 THUMB_TIP
        # 食指:MCP 略上
        [0.47, 0.62, 0],  # 5 INDEX_MCP
        [0.49, 0.52, 0],  # 6 INDEX_PIP
        [0.45, 0.48, 0],  # 7 INDEX_DIP (向内回)
        [0.42, 0.44, 0],  # 8 INDEX_TIP
        # 中指
        [0.52, 0.62, 0],  # 9 MIDDLE_MCP
        [0.54, 0.51, 0],  # 10 MIDDLE_PIP
        [0.50, 0.47, 0],  # 11 MIDDLE_DIP
        [0.47, 0.43, 0],  # 12 MIDDLE_TIP
        # 无名指
        [0.57, 0.63, 0],  # 13 RING_MCP
        [0.59, 0.52, 0],  # 14 RING_PIP
        [0.55, 0.48, 0],  # 15 RING_DIP
        [0.52, 0.45, 0],  # 16 RING_TIP
        # 小指
        [0.62, 0.64, 0],  # 17 PINKY_MCP
        [0.64, 0.54, 0],  # 18 PINKY_PIP
        [0.60, 0.51, 0],  # 19 PINKY_DIP
        [0.58, 0.48, 0],  # 20 PINKY_TIP
    ]

    if pose_type == 'perfect':
        # 理想手型:5 指自然弯曲 75-90°,手弓明显
        return base

    elif pose_type == 'tense':
        # 紧张:手指全直 (180°),手腕抬高
        tense = [p[:] for p in base]
        for p in tense:
            p[1] -= 0.08  # 整体上移
        # 把所有 DIP/TIP 移到 PIP-MCP 的延长线上(直)
        for finger_mcp_pip_tip in [(5, 6, 8), (9, 10, 12), (13, 14, 16), (17, 18, 20)]:
            mcp = tense[finger_mcp_pip_tip[0]]
            pip = tense[finger_mcp_pip_tip[1]]
            # TIP 在 PIP + 1.5 * (PIP - MCP) (伸直)
            dx = pip[0] - mcp[0]
            dy = pip[1] - mcp[1]
            tense[finger_mcp_pip_tip[2]] = [pip[0] + dx * 1.2, pip[1] + dy * 1.2, 0]
            # DIP 也伸直
            tense[finger_mcp_pip_tip[1] + 1] = [pip[0] + dx * 0.5, pip[1] + dy * 0.5, 0]
        return tense

    elif pose_type == 'collapsed':
        # 塌陷:手腕下沉,手弓过深
        coll = [p[:] for p in base]
        for p in coll:
            p[1] += 0.05
        # 手弓过深:所有 PIP 更往上 + TIP 更往下
        for i in [6, 10, 14, 18]:  # PIP
            coll[i][1] -= 0.06
        for i in [4, 8, 12, 16, 20]:  # TIP
            coll[i][1] += 0.04
        return coll

    elif pose_type == 'asymmetric':
        # 不对称:4/5 指伸直(独立性弱)
        asym = [p[:] for p in base]
        for finger_mcp_pip_tip in [(13, 14, 16), (17, 18, 20)]:
            mcp = asym[finger_mcp_pip_tip[0]]
            pip = asym[finger_mcp_pip_tip[1]]
            dx = pip[0] - mcp[0]
            dy = pip[1] - mcp[1]
            asym[finger_mcp_pip_tip[2]] = [pip[0] + dx * 1.2, pip[1] + dy * 1.2, 0]
            asym[finger_mcp_pip_tip[1] + 1] = [pip[0] + dx * 0.5, pip[1] + dy * 0.5, 0]
        return asym

    return base


# === MediaPipe 集成 (如可用) ===

def extract_landmarks_from_image(image_path: str) -> list | None:
    """
    从图片提取 MediaPipe 21 关键点
    如果 MediaPipe 不可用,返回 None
    """
    try:
        import cv2
        import mediapipe as mp
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(
            static_image_mode=True,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        image = cv2.imread(image_path)
        if image is None:
            return None
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)
        hands.close()
        if not results.multi_hand_landmarks:
            return None
        out = []
        for hand_lms in results.multi_hand_landmarks:
            pts = []
            for lm in hand_lms.landmark:
                pts.append([lm.x, lm.y, lm.z])
            out.append(pts)
        return out
    except ImportError:
        return None


# === voice_dialog 集成 ===

def patch_voice_dialog_with_hand_pose(dialog_module=None):
    """
    注入到 voice_dialog,识别"手型"意图
    用法: patch_voice_dialog_with_hand_pose(voice_dialog)
    然后说 "分析我的手型" 自动跑
    """
    def handle_hand_pose_request(text: str) -> str | None:
        text_lower = text.lower()
        # 中文/英文意图识别
        keywords = ['手型', '手姿', '手的姿势', 'hand pose', 'hand posture', '手部姿态']
        if not any(kw in text_lower for kw in keywords):
            return None

        # 用完美手型做默认 demo
        landmarks = generate_test_hand_pose('perfect')
        result = analyze_hand_pose(landmarks)

        # 简洁摘要
        s = f"你的手型综合分 {result['overall_score']} ({result['grade']})\n"
        s += "9 维度: " + ", ".join([
            f"{k}={v:.0f}" for k, v in result['dimensions'].items()
        ]) + "\n"
        if result['suggestions']:
            s += "教学建议:\n"
            for sug in result['suggestions']:
                s += f"- [{sug['severity']}] {sug['advice']}\n"
        return s

    if dialog_module is None:
        return handle_hand_pose_request

    # 捕获原始 call_llm 避免递归
    _orig_call_llm = dialog_module.call_llm if hasattr(dialog_module, 'call_llm') else None

    if hasattr(dialog_module, 'register_intent_handler'):
        dialog_module.register_intent_handler('hand_pose', handle_hand_pose_request)
        return True
    elif hasattr(dialog_module, 'process_query'):
        # Monkey patch
        def patched_process_query(text, *args, **kwargs):
            handled = handle_hand_pose_request(text)
            if handled:
                return handled
            return _orig_call_llm(text, *args, **kwargs) if _orig_call_llm else None
        dialog_module.process_query = patched_process_query
        return True
    return False


# === CLI ===

def main():
    """CLI: 演示 4 种手型"""
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--pose', default='perfect',
                   choices=['perfect', 'tense', 'collapsed', 'asymmetric', 'all'])
    p.add_argument('--json', action='store_true', help='JSON output')
    p.add_argument('--both-hands', action='store_true', help='左右手分析')
    p.add_argument('--image', help='Extract from image (MediaPipe)')
    args = p.parse_args()

    if args.image:
        hands = extract_landmarks_from_image(args.image)
        if not hands:
            print("ERROR: MediaPipe 不可用或未检测到手", file=sys.stderr)
            sys.exit(1)
        result = analyze_hand_pose(hands[0])
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_hand_pose_report(result)
        return

    if args.pose == 'all':
        for pt in ['perfect', 'tense', 'collapsed', 'asymmetric']:
            print(f"\n=== {pt.upper()} ===")
            lm = generate_test_hand_pose(pt)
            if args.both_hands:
                # 生成"左"略不同的手
                lm_l = generate_test_hand_pose('perfect' if pt == 'perfect' else 'asymmetric')
                result = analyze_hand_pose(lm, lm_l, lm)
            else:
                result = analyze_hand_pose(lm)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print_hand_pose_report(result)
    else:
        lm = generate_test_hand_pose(args.pose)
        if args.both_hands:
            lm_l = generate_test_hand_pose('perfect' if args.pose == 'perfect' else 'asymmetric')
            result = analyze_hand_pose(lm, lm_l, lm)
        else:
            result = analyze_hand_pose(lm)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_hand_pose_report(result)


def print_hand_pose_report(r: dict):
    print("\n=== 钢琴手型 9 维度分析 ===")
    print(f"综合分: {r['overall_score']} ({r['grade']})")
    print("\n维度分数 (0-100):")
    for k, v in r['dimensions'].items():
        bar = "█" * int(v / 10) + "░" * (10 - int(v / 10))
        print(f"  {k:24s} {bar} {v}")
    print("\n各指角度:")
    for finger, info in r['finger_details'].items():
        print(f"  {finger:8s} {info['angle']}° (score {info['score']})")
    if r['suggestions']:
        print(f"\n教学建议 ({len(r['suggestions'])} 项):")
        for i, s in enumerate(r['suggestions'], 1):
            print(f"  {i}. [{s['severity']}] {s['dimension']}={s['score']}")
            print(f"     → {s['advice']}")
    else:
        print("\n✅ 你的手型很好,继续保持!")


if __name__ == '__main__':
    main()
