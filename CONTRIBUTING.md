# Contributing to CoPiano

Thanks for your interest in CoPiano! 🎹

## Quick Start

```bash
# Fork + clone
git clone https://github.com/your-username/copiano.git
cd copiano

# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pytest                              # 跑测试 (需要本地 PG + Redis)

# Web
cd ../web
npm install
cp .env.example .env.local
npm run dev                         # → http://localhost:3000
```

## Development Workflow

1. **挑一个任务** — 看 [GitHub Issues](../../issues) 找 `good first issue` 标签
2. **创建分支** — `git checkout -b feat/your-feature`
3. **改代码** — 写测试 + 跑现有测试
4. **提交** — `git commit -m "feat(scope): 简明描述"` (用 conventional commits)
5. **开 PR** — 用 `.github/PULL_REQUEST_TEMPLATE.md` 模板

## Commit Message Convention

```
<type>(<scope>): <short description>

<body>

<footer>
```

**Types**: `feat` / `fix` / `docs` / `refactor` / `test` / `chore` / `perf`
**Scope**: `backend` / `web` / `docs` / `scripts` / `ci`

例: `feat(web): add VexFlow staff display for sight-reading`

## Code Style

### Backend (Python)
- ruff check (line length 100, 启用 pyupgrade, bugbear, comprehensions)
- pytest 全部测试必须过
- Pydantic v2 schemas
- async/await 优先

### Web (TypeScript)
- ESLint (next/core-web-vitals)
- Prettier (single quote, 100 width)
- TypeScript strict
- shadcn/ui 风格组件

## Pull Request Checklist

- [ ] 测试覆盖
- [ ] CI 通过 (`.github/workflows/ci.yml`)
- [ ] 文档更新 (如果加了功能)
- [ ] 截图 (UI 改动)
- [ ] 不引入新依赖 (除非必要,先讨论)

## Areas We'd Love Help

- 🎼 **乐理 / 音乐教育** — 改进 5 维评估算法, 加更多表现力维度
- 🤖 **LLM 提示工程** — 更好的银发模式简化, 反馈结构化输出
- 🎨 **UI/UX** — 银发模式可视化, 移动端优化
- 📱 **iOS App** — Swift/SwiftUI (Phase 7B 待启动)
- 🌐 **国际化** — 英文 / 日文版本
- 📊 **数据可视化** — 5 维雷达图 / 进步曲线
- 🐛 **Bug 修复** — 看 [Issues](../../issues?q=is%3Aopen+label%3Abug)
- 📝 **文档** — 翻译 / 教程 / 视频

## Communication

- GitHub Issues: 提 bug / 建议
- Email: <hi@yefzyj.top> 商务 / 媒体
- 微信公众号: CoPiano_Official (产品公告)

## Code of Conduct

Be respectful. No harassment. We're all here to make piano learning accessible to everyone, especially 长者 and kids.

## License

By contributing, you agree your contributions will be licensed under the [MIT License](LICENSE).
