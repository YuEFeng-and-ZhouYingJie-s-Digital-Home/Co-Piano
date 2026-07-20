# Cycle 5 测试报告 — 银发/长辈模式

**结果**: 34 / 34 通过

## 4 大开关验证

1. **TTS 慢速**: speed=0.85, volume=1.2 ✅
2. **LLM 简化**: jargon 替换 + 鼓励词 + 长度截断 ✅
3. **超时延长**: VAD 3s, dialog 10s (vs 1.5s/5s) ✅
4. **鼓励反馈**: 13 条鼓励词 + 您/好的 等尊重词 ✅

## 详细测试

| 测试 | 结果 | 详情 |
|------|------|------|
| jargon_rubato | ✅ | 'rubato' → '自由伸缩节拍' in: 练习是最好的老师,你已经做得很好了。 请练习 自由伸缩节拍 来表达情感。 |
| jargon_ritardando | ✅ | 'ritardando' → '逐渐变慢' in: 我陪你一起练,不急。 请练习 逐渐变慢 来表达情感。 |
| jargon_crescendo | ✅ | 'crescendo' → '逐渐变响' in: 继续加油,每天进步一点点! 请练习 逐渐变响 来表达情感。 |
| jargon_对位 | ✅ | '对位' → '两个声部的配合' in: 我陪你一起练,不急。 请练习 两个声部的配合 来表达情感。 |
| jargon_力度 | ✅ | '力度' → '按琴的轻重' in: 别着急,慢慢来,弹琴本来就要练很多遍。 请练习 按琴的轻重 来表达情感。 |
| jargon_琶音 | ✅ | '琶音' → '从低到高依次弹' in: 您的努力我看得到,真棒! 请练习 从低到高依次弹 来表达情感。 |
| jargon_staccato | ✅ | 'staccato' → '跳音' in: 继续加油,每天进步一点点! 请练习 跳音,每个音分开弹短促 来表达情感。 |
| length_limit | ✅ | input=200 output=161 (max 175 = 150 + 鼓励词 buffer) |
| encouragement_skip_when_present | ✅ | output: 您的 Allegro 段落弹得不错。 |
| encouragement_inject_when_absent | ✅ | output: 每一首名曲都是这样慢慢练出来的,您做得很好。 Allegro 段落需要练。 |
| append_to_existing_system | ✅ | system length: 312 |
| insert_new_system | ✅ | first role: system |
| tts_speed | ✅ | speed=0.85 |
| tts_volume | ✅ | volume=1.2 |
| age_None | ✅ | age=None → auto_senior=False (expected False) |
| age_25 | ✅ | age=25 → auto_senior=False (expected False) |
| age_59 | ✅ | age=59 → auto_senior=False (expected False) |
| age_60 | ✅ | age=60 → auto_senior=True (expected True) |
| age_75 | ✅ | age=75 → auto_senior=True (expected True) |
| patch_no_age | ✅ | result: True |
| default_no_senior | ✅ | got: Allegro 段落需要练。 |
| turn_on_intent | ✅ | got: 好的,已开启长辈模式。我会说得慢一点,声音大一点,多用大白话,您别着急,我们一起慢慢练。 |
| simplified_in_senior_mode | ✅ | got: 您这段 Allegro 弹得不错,建议练习 自由伸缩节拍 和 逐渐变响。 |
| turn_off_intent | ✅ | got: 好的,已关闭长辈模式,恢复正常语速。 |
| back_to_normal_after_off | ✅ | got: Allegro 段落需要练。 |
| no_recursion | ✅ | call_count: 3 (expected 3) |
| 35_age_no_auto | ✅ | got: [原始] test |
| 60_age_auto | ✅ | got: 继续加油,每天进步一点点! [银发] test |
| 75_age_auto | ✅ | got: 继续加油,每天进步一点点! [银发] test |
| wcag_jargon_replaced | ✅ | rubato replaced: True, free time phrase: True |
| wcag_crescendo_replaced | ✅ | crescendo replaced: True, gradual louder: True |
| wcag_length_limited | ✅ | input=240 output=143 (max 170) |
| wcag_encouraging_tone | ✅ | contains encouraging word: True |
| speed | ✅ | 0.02 ms/simplify |
