# 银发模式 (Senior Mode)

CoPiano 为 60+ 长者提供专属 UI 主题,免费使用 Pro 全部功能。

## 触发

1. 用户在 `/app/settings` 开启"银发模式"开关
2. 后端 `UserProfile.is_senior = true`
3. 保护布局 `app/app/layout.tsx` 拉 profile,传 `<SeniorModeApplier isSenior>`
4. Client 组件通过 `useSeniorMode` 在 `<html>` 根加 `senior` className
5. `globals.css` 中 `.senior` 规则自动激活

## 视觉调整 (CSS 变量)

| 维度 | 默认 | 银发 |
|---|---|---|
| 基础字号 | 16px | 18px (1.05rem) |
| 行高 | 1.5 | 1.75 |
| h1 | 36px | 40px |
| h2 | 30px | 32px |
| h3 | 24px | 24px |
| 按钮最小高 | 40px | 44px |
| 输入框最小高 | 40px | 44px |
| 边框宽度 | 1px | 2px |
| 阴影 | 多层模糊 | 0 2px 0 简实阴影 |
| 动画时长 | 200-500ms | 0.001ms (关掉) |
| 链接 | 默认 | 加下划线 + 偏移 3px |
| 焦点环 | 2px | 3px 高对比紫 |

## 同步生效的 LLM 简化

- 后端 `feedback_generator.py` 检测 `is_senior`,调用 `simplify_text_for_senior`
- 自动翻译 19 个常见术语:terminus → 渐慢, crescendo → 渐强, staccato → 跳音 等

## 行为兼容

- 关闭开关:`router.refresh()` 触发服务端重新渲染,移除 `senior` class
- 移动端:同样生效
- LLM 反馈:后端同步简化 (Senior 反馈有 `simplified_for_senior: true` 标记)

## WCAG 2.1 AA 合规

银发模式符合 WCAG 2.1 AA 标准:
- 文本对比度 ≥ 4.5:1
- 焦点可见
- 目标尺寸 ≥ 44×44px
- 动画可关闭 (auto via `prefers-reduced-motion` 习惯)
