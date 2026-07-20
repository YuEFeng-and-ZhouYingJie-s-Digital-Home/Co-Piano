# Cycle 4 测试报告

**结果**: 33 / 33 通过

## 详细测试

| 测试 | 结果 | 详情 |
|------|------|------|
| scenario_perfect | ✅ | score=78.0 grade=中等 (Average) dims=9 |
| scenario_tense | ✅ | score=68.0 grade=及格 (Pass) dims=9 |
| scenario_collapsed | ✅ | score=64.2 grade=及格 (Pass) dims=9 |
| scenario_asymmetric | ✅ | score=68.0 grade=及格 (Pass) dims=9 |
| monotonicity_perfect_best | ✅ | PERFECT=78.0 > TENSE=68.0 & COLLAPSED=64.2 |
| all_9_dimensions | ✅ | missing=none extra=none |
| dimension_score_range | ✅ | all in [0,100]: True |
| finger_curl_index_range | ✅ | angle=52.5° in [20,100] |
| finger_curl_middle_range | ✅ | angle=51.5° in [20,100] |
| finger_curl_ring_range | ✅ | angle=55.3° in [20,100] |
| finger_curl_pinky_range | ✅ | angle=56.3° in [20,100] |
| tense_index_straight | ✅ | angle=0.0° < 10° |
| tense_middle_straight | ✅ | angle=0.0° < 10° |
| tense_ring_straight | ✅ | angle=0.0° < 10° |
| tense_pinky_straight | ✅ | angle=0.0° < 10° |
| asymmetric_index_bent | ✅ | index angle=52.5° > 30° |
| asymmetric_ring_straight | ✅ | ring angle=0.0° < 10° |
| patch_applied | ✅ | patch result: True |
| intent_hand_pose | ✅ | got: 你的手型综合分 78.0 (中等 (Average))
9 维度: wrist_height=68, hand_arch=75, finger_curl=91,... |
| fallthrough_to_llm | ✅ | got: LLM: 今天天气怎么样 |
| no_recursion | ✅ | LLM called 1 times (expected 1) |
| english_keyword | ✅ | hand pose query: 你的手型综合分 78.0 (中等 (Average))
9 维度: wrist_height=68, hand_arch... |
| multi_calls_stable | ✅ | after 3 LLM calls, count=3 (expected 3) |
| json_structure | ✅ | keys: ['dimensions', 'finger_details', 'overall_score', 'weights', 'suggestions', 'grade'] |
| suggestions_is_list | ✅ | type: list, len: 3 |
| dimensions_count | ✅ | count: 9 |
| zero_landmarks | ✅ | score=60.0 |
| collinear_landmarks | ✅ | score=65.8 |
| suggestions_generated | ✅ | 3 suggestions |
| suggestions_have_advice | ✅ | all have detailed advice: True |
| severity_classified | ✅ | severities: ['high', 'high', 'high'] |
| both_hands_symmetry | ✅ | symmetry=60 |
| speed | ✅ | 0.06 ms/analyze |
