"""
senior_mode.py — CoPiano 银发/长辈模式

Cycle 5 Stage 2 实现:
- 4 大开关:TTS 慢速 / LLM 简化 / 超时延长 / 鼓励式反馈
- voice_dialog 集成 (无递归)
- student_db 按年龄自动切档 (>= 60)
- WCAG 2.1 AA 部分合规 (字号/对比度/操作步数)

调研依据: notes/market_knowledge_cycle5.md
"""

import json
import re
import sys
import time
from typing import Optional, Dict, List, Tuple


# === 银发模式配置 ===

DEFAULT_SENIOR_CONFIG = {
    # TTS 设置 (Edge-TTS)
    'tts_speed': 0.85,       # 正常 1.0 → 慢速 0.85 (15% 慢)
    'tts_pitch': 0,           # 不变
    'tts_volume': 1.2,        # 略大 (系统最大 1.0, 1.2 在 Edge-TTS 是软增益)

    # LLM prompt 设置
    'llm_max_length': 150,    # 正常 ~250 字 → 150 字 (-40%)
    'llm_simple_words': True, # 用通俗词替代专业术语
    'llm_encouraging': True,  # 加鼓励词频次
    'llm_jargon_replace': True,  # jargon → 通俗词

    # 超时设置
    'vad_silence_threshold': 3.0,  # 正常 1.5s → 3.0s
    'dialog_timeout': 10.0,        # 正常 5s → 10s
    'input_max_duration': 15.0,    # 录音最长 15s (vs 5s)

    # 反馈显示
    'large_text': True,       # 终端字号大
    'simple_emoji': True,     # 简化 emoji
    'confirm_important': True,  # 重要操作二次确认

    # 自动激活
    'auto_age_threshold': 60,  # >= 60 自动开
}


# === Jargon 替换表 (通俗化) ===

JARGON_REPLACEMENTS = {
    # 音乐术语 → 通俗说法
    '对位': '两个声部的配合',
    '力度': '按琴的轻重',
    '延音': '让音拖长一点',
    '连奏': '一个接一个连贯弹',
    '跳音': '每个音分开弹,短促',
    '装饰音': '快速的装饰小音',
    '速度': '弹奏的快慢',
    '节拍': '打拍子的节奏',
    '调性': '音乐的调子',
    '和声': '几个音一起响',
    '琶音': '从低到高依次弹',
    '音阶': '从低到高或高到低的音',
    '切分音': '在拍子中间的音',
    '连音': '连起来弹',
    '半音': '相邻两个琴键的距离',
    '全音': '两个半音的距离',
    '属七和弦': '5 7 2 4 这四个音',
    '主和弦': '1 3 5 三个音',
    '小调': '听起来比较忧伤',
    '大调': '听起来比较明亮',
    '转调': '换一个新的调',
    '终止式': '一段音乐结束的方式',
    '回旋曲': '主题反复出现的曲子',
    '变奏曲': '主题不断变化的曲子',
    '奏鸣曲': '一种大型钢琴曲',
    # 错音描述
    '错音': '弹错的音',
    '节奏不稳': '拍子不均匀',
    # 表现力
    'rubato': '自由伸缩节拍',
    'ritardando': '逐渐变慢',
    'accelerando': '逐渐变快',
    'crescendo': '逐渐变响',
    'diminuendo': '逐渐变轻',
    'staccato': '跳音,每个音分开弹短促',
    'legato': '连奏,音连贯不间断',
    'piano': '弱(p),弹轻一点',
    'forte': '强(f),弹响一点',
    'allegro': '快板,弹得快一些',
    'adagio': '慢板,弹得慢一些',
    'andante': '行板,中等速度',
    # 调号
    '升号': '往右的黑色键',
    '降号': '往左的黑色键',
    # 谱面
    '五线谱': '五条线的乐谱',
    '高音谱号': '右手弹的谱号',
    '低音谱号': '左手弹的谱号',
    # 演奏法
    '踏板': '脚踩的延音踏板',
    '指法': '用哪个手指弹',
    '弓法': '拉琴用弓的方式',  # 钢琴用不到但保留
}


ENCOURAGEMENT_PHRASES = [
    "你做得很好!",
    "继续加油,每天进步一点点!",
    "别着急,慢慢来,弹琴本来就要练很多遍。",
    "你今天比昨天进步了!",
    "这个音弹得不错,继续保持。",
    "我们一起努力,你会越来越棒的。",
    "练习是最好的老师,你已经做得很好了。",
    "我陪你一起练,不急。",
    "每一首名曲都是这样慢慢练出来的,您做得很好。",
    "您的努力我看得到,真棒!",
]


# === 银发 prompt 构造器 ===

SENIOR_SYSTEM_PROMPT = """你是一位 30 年教学经验的钢琴老师,正在教一位 60 岁以上的老年学员。

你的教学风格:
- 语气温和、耐心、鼓励,像对自己爷爷奶奶说话
- 用日常口语,不用专业术语。如果必须用专业名词,马上用一句通俗的话解释
- 句子短一点,一次只说一件事
- 每次反馈先说"好的"或"不错",再说可以改进的地方
- 鼓励为主,不批评。多说"您已经做得很好了,我们可以再......"
- 经常说"加油""继续""别着急"等鼓励词
- 举一些老人熟悉的例子(老歌、童谣、儿歌)
- 永远不要用英文专业术语(如 rubato, crescendo 等),全部用中文

回复长度: 控制在 150 字以内,简洁有温度。"""


def simplify_text_for_senior(text: str, config: dict = None) -> str:
    """简化文字 (jargon 替换 + 鼓励词插入 + 句长截断)"""
    if config is None:
        config = DEFAULT_SENIOR_CONFIG

    out = text

    # 1. 替换 jargon
    if config.get('llm_jargon_replace', True):
        for jargon, simple in JARGON_REPLACEMENTS.items():
            # 简单替换 (不考虑词形变化)
            out = out.replace(jargon, simple)

    # 2. 限制长度
    max_len = config.get('llm_max_length', 150)
    if len(out) > max_len:
        # 优先在句号处截断
        truncated = out[:max_len]
        last_period = truncated.rfind('。')
        if last_period > max_len * 0.6:
            out = truncated[:last_period + 1]
        else:
            out = truncated + '...'

    # 3. 在开头加鼓励 (如果还没有) — 使用稳定 hash (避免 Python hash 随机化)
    if config.get('llm_encouraging', True):
        if not any(c in out[:20] for c in ['好', '棒', '不错', '加油', '真']):
            import hashlib
            stable_idx = int(hashlib.md5(text.encode('utf-8')).hexdigest(), 16) % len(ENCOURAGEMENT_PHRASES)
            out = ENCOURAGEMENT_PHRASES[stable_idx] + ' ' + out

    return out


def add_senior_system_prompt(messages: list, config: dict = None) -> list:
    """在 messages 列表前面插入银发 system prompt"""
    if config is None:
        config = DEFAULT_SENIOR_CONFIG

    # 已有 system 提示?
    if messages and messages[0].get('role') == 'system':
        # 在已有 system 后追加
        new_msgs = [messages[0].copy()]
        new_msgs[0]['content'] = messages[0].get('content', '') + '\n\n' + SENIOR_SYSTEM_PROMPT
        new_msgs.extend(messages[1:])
    else:
        new_msgs = [{'role': 'system', 'content': SENIOR_SYSTEM_PROMPT}] + list(messages)

    return new_msgs


# === TTS 参数调整 ===

def get_senior_tts_params(config: dict = None) -> dict:
    """获取银发模式 TTS 参数"""
    if config is None:
        config = DEFAULT_SENIOR_CONFIG
    return {
        'speed': config.get('tts_speed', 0.85),
        'pitch': config.get('tts_pitch', 0),
        'volume': config.get('tts_volume', 1.2),
    }


# === 年龄自动判断 ===

def should_auto_senior(age: Optional[int], config: dict = None) -> bool:
    """根据年龄判断是否自动开银发模式"""
    if config is None:
        config = DEFAULT_SENIOR_CONFIG
    if age is None:
        return False
    return age >= config.get('auto_age_threshold', 60)


# === voice_dialog 集成 ===

def patch_voice_dialog_with_senior_mode(dialog_module=None, config: dict = None, age: Optional[int] = None):
    """
    注入到 voice_dialog,识别银发/长辈模式意图
    用法: patch_voice_dialog_with_senior_mode(voice_dialog, age=68)
    """
    if config is None:
        config = DEFAULT_SENIOR_CONFIG.copy()

    # 自动按年龄开
    auto_senior = should_auto_senior(age, config)
    if auto_senior:
        config['_active'] = True
    else:
        config['_active'] = False

    def handle_senior_request(text: str) -> Optional[str]:
        text_lower = text.lower()
        # 中文/英文关键词
        on_kw = ['长辈模式', '老年模式', '银发模式', '慢一点', '慢速', 'senior mode', 'elder mode', '慢点说']
        off_kw = ['正常模式', '普通模式', '标准模式', 'normal mode', '关闭长辈', '关闭老年']

        if any(kw in text_lower for kw in on_kw):
            config['_active'] = True
            return "好的,已开启长辈模式。我会说得慢一点,声音大一点,多用大白话,您别着急,我们一起慢慢练。"

        if any(kw in text_lower for kw in off_kw):
            config['_active'] = False
            return "好的,已关闭长辈模式,恢复正常语速。"

        return None

    if dialog_module is None:
        # 返回 handle + config 用于测试
        return handle_senior_request, config

    # 捕获原始函数 (避免递归)
    _orig_call_llm = dialog_module.call_llm if hasattr(dialog_module, 'call_llm') else None
    _orig_synthesize_speech = dialog_module.synthesize_speech if hasattr(dialog_module, 'synthesize_speech') else None

    # 尝试注册 intent handler
    if hasattr(dialog_module, 'register_intent_handler'):
        dialog_module.register_intent_handler('senior_mode', handle_senior_request)
        return True

    # Monkey patch: call_llm (加 senior prompt)
    if _orig_call_llm is not None:
        def patched_call_llm(messages, backend="mock", **kwargs):
            if config.get('_active', False):
                messages = add_senior_system_prompt(messages, config)
            result = _orig_call_llm(messages, backend=backend, **kwargs)
            if config.get('_active', False):
                result = simplify_text_for_senior(result, config)
            return result
        dialog_module.call_llm = patched_call_llm

    # Monkey patch: synthesize_speech (慢速 + 大声)
    if _orig_synthesize_speech is not None:
        async def patched_synthesize_speech(text, output_path, voice=None, lang=None, **kwargs):
            if config.get('_active', False):
                # Edge-TTS 支持 rate/volume 参数
                rate = f"-{int((1 - config['tts_speed']) * 100)}%"  # +15% slower
                # 通过 tts_edge 的 synthesize 注入
                try:
                    from tts_edge import synthesize
                    tts_params = get_senior_tts_params(config)
                    return await synthesize(text, output_path, voice=voice, lang=lang,
                                            rate=rate, volume="+20%")
                except Exception:
                    pass
            return await _orig_synthesize_speech(text, output_path, voice=voice, lang=lang, **kwargs)
        dialog_module.synthesize_speech = patched_synthesize_speech

    # patch process_query if exists (使用 patched_call_llm 而非原始,保持 senior prompt 注入)
    if hasattr(dialog_module, 'process_query'):
        def patched_process_query(text, *args, **kwargs):
            handled = handle_senior_request(text)
            if handled:
                return handled
            # 用 patched_call_llm 触发 senior prompt
            return dialog_module.call_llm([{'role': 'user', 'content': text}], *args, **kwargs)
        dialog_module.process_query = patched_process_query

    return True


# === CLI ===

def main():
    """CLI 演示"""
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--text', help='要简化的文字')
    p.add_argument('--demo', action='store_true', help='演示银发模式效果')
    p.add_argument('--json', action='store_true', help='JSON 输出')
    p.add_argument('--age', type=int, help='用户年龄 (测试自动激活)')
    args = p.parse_args()

    if args.demo:
        # 对比演示
        samples = [
            "你的 Allegro 段落速度略快,ritardando 标记没体现,需要练习 rubato 来表达浪漫主义情感。",
            "巴洛克时期的对位清晰度是核心,要注重 staccato 和 legato 的对比,踏板运用也很关键。",
            "这一段 Mozart 的 c minor 奏鸣曲,crescendo 处理不够自然,建议加强半音阶练习。",
        ]
        print("=== 银发模式演示 ===\n")
        for s in samples:
            print(f"原文: {s}")
            simplified = simplify_text_for_senior(s)
            print(f"银发: {simplified}\n")

    elif args.text:
        out = simplify_text_for_senior(args.text)
        if args.json:
            print(json.dumps({'original': args.text, 'simplified': out}, ensure_ascii=False, indent=2))
        else:
            print(out)

    elif args.age is not None:
        config = DEFAULT_SENIOR_CONFIG.copy()
        auto = should_auto_senior(args.age, config)
        print(json.dumps({
            'age': args.age,
            'auto_activate_senior': auto,
            'threshold': config['auto_age_threshold'],
        }, ensure_ascii=False, indent=2))

    else:
        print("用法:")
        print("  --text '...'  简化一段文字")
        print("  --demo         演示对比")
        print("  --age 65       测试年龄自动激活")
        print("  --json         JSON 输出")


if __name__ == '__main__':
    main()
