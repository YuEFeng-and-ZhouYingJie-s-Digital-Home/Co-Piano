# CoPiano GitHub 仓库管理员操作手册

> 仓库: https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano
> 当前管理员: 你 (YueFeng)
> 权限: admin / maintain / push / triage / pull (全开)
> 创建时间: 2026-07-27
> 类型: public
> 默认分支: main
> 描述 (已有): "In our point of view, the most exciting thing in the world is playing the piano on a boat floating over the sea while facing the moon and the wind. Therefore, we build this program called Co-Piano, to allow everyone playing piano without loneliness."

---

## 🚨 0. 安全:Token 已暴露,立即撤销

**当前 token `ghp_…REDACTED…` 曾在 chat history / shell history 暴露,必须撤销**:

1. 打开 https://github.com/settings/tokens
2. 找到这个 token,点 **Delete** (右上角)
3. 重新生成: 
   - Note: `CoPiano-deploy-2026Q3`
   - Expiration: **30 天**(强制过期)
   - Scopes: 只勾 `repo` + `workflow`(其它都不要)
4. 新 token 通过 1Password CLI 用:
   ```bash
   op read "op://Private/CoPiano GitHub PAT/token"
   ```

---

## 📋 1. 仓库基础信息

| 项 | 值 |
|---|---|
| **完整路径** | `YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano` |
| **HTML URL** | https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano |
| **Clone (HTTPS)** | `https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano.git` |
| **Clone (SSH)** | `git@github.com:YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano.git` |
| **默认分支** | `main` |
| **可见性** | public |
| **Web 特性** | Issues ✅ / Projects ✅ / Wiki ✅ |
| **GitHub Pages** | ❌ 未启用 |
| **Topics** | ❌ 空 (待补) |
| **Stars / Forks** | 0 / 0 |
| **管理员** | 你 (admin) |

### 1.1 建议立即补的 Settings → General

```
Description: AI classical piano coach — 5-dim evaluation + 7-day adaptive curriculum + RCT d=1.34. Senior mode free.
Website:      https://yefzyj.top
Topics:       ai, music, piano, classical-piano, education, web-midi, fastapi, nextjs, postgresql
```

设置位置: https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano/settings

---

## 🔒 2. 分支保护 (Branch Protection)

### 2.1 `main` 分支(必开)

**位置**: Settings → Branches → Add rule → Branch name pattern: `main`

| 设置 | 推荐值 |
|---|---|
| Require a pull request before merging | ✅ |
| → Required approvals | **1** |
| → Dismiss stale pull request approvals | ✅ |
| → Require review from Code Owners | ✅ |
| Require status checks to pass | ✅ |
| → Require branches up to date | ✅ |
| → Required checks | (跑通 CI 后选) `Backend tests` / `Web build` |
| Require conversation resolution | ✅ |
| Require signed commits | ❌ (本项目不强制) |
| Require linear history | ❌ (允许 merge commit) |
| Include administrators | ✅ |
| Allow force pushes | ❌ (严禁) |
| Allow deletions | ❌ |

### 2.2 `develop` 分支(可选,后续用)

分支名 pattern: `develop`,规则松一些 (0 approval, status checks only)

---

## 🤝 3. CODEOWNERS (自动指派审查人)

**新建文件**: `.github/CODEOWNERS`

```
# Default owner for everything
*                          @yuefeng

# Backend
/backend/                  @yuefeng
/backend/app/api/          @yuefeng
/backend/app/services/     @yuefeng
/backend/app/models/       @yuefeng

# Web
/web/                      @yuefeng
/web/app/                  @yuefeng
/web/components/           @yuefeng

# Docs & scripts
/docs/                     @yuefeng
/scripts/                  @yuefeng

# CI / 安全
/.github/                  @yuefeng
*.yml                     @yuefeng
SECURITY.md               @yuefeng
```

(等团队多人时改成 `@org/team-name`)

---

## 🔐 4. GitHub Secrets (CI 用)

**位置**: Settings → Secrets and variables → Actions → New repository secret

### 4.1 必需的 Secrets (CI backend 测试)

| Secret 名 | 值 | 说明 |
|---|---|---|
| `BACKEND_DATABASE_URL` | `postgresql+asyncpg://copiano:testpass@127.0.0.1:5432/copiano_test` | CI test DB (service container) |
| `BACKEND_REDIS_URL` | `redis://127.0.0.1:6379/0` | CI test Redis |
| `BACKEND_JWT_SECRET` | `ci-only-secret-not-for-prod-32chars` | 32+ 字符 random |

### 4.2 部署相关 Secrets (后续 deploy job 用)

| Secret 名 | 值 | 说明 |
|---|---|---|
| `DEPLOY_SSH_KEY` | `cat ~/Downloads/123.pem` 全文 | 整段 PEM 私钥 |
| `DEPLOY_HOST` | `ubuntu@124.156.184.160` | 服务器 SSH |
| `DEPLOY_PORT` | `22` | SSH 端口 |
| `MINIO_ACCESS_KEY` | `copiano` | (A3.5 已有) |
| `MINIO_SECRET_KEY` | `mNioCopiano2026Secret` | (A3.5 已有) |
| `PG_PASSWORD` | `GHMFjIjUQCxDC4017QZpqorvYjjWDfHc` | (A1.6 已有) |
| `REDIS_PASSWORD` | `sNbnGWJwnx2hLtaeGd7CcEQ3nMnmbzHr` | (A1.6 已有) |
| `OPENAI_API_KEY` | (待你提供) | LLM 兜底 |
| `NEXTAUTH_SECRET` | `$(openssl rand -base64 32)` | NextAuth session |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | (待你提供) | OAuth |
| `APPLE_CLIENT_ID` / `APPLE_CLIENT_SECRET` | (待你提供) | Apple Sign In |

### 4.3 可选但推荐

| Secret | 说明 |
|---|---|
| `CODECOV_TOKEN` | Codecov.io 覆盖率徽章 (https://codecov.io 申请) |
| `SLACK_WEBHOOK_URL` | CI 失败 Slack 通知 |
| `LHCI_GITHUB_APP_TOKEN` | Lighthouse CI 集成 (性能监控) |

### 4.4 Variables (非敏感)

**位置**: Settings → Secrets and variables → Actions → Variables tab

| Variable | 值 |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `https://api.yefzyj.top` |
| `NEXT_PUBLIC_MARKETING_URL` | `https://yefzyj.top` |
| `NEXT_PUBLIC_WS_BASE_URL` | `wss://api.yefzyj.top` |
| `NEXT_PUBLIC_APP_URL` | `https://app.yefzyj.top` |
| `ENVIRONMENT` | `production` |

---

## 🌍 5. Environments (生产环境保护)

**位置**: Settings → Environments → New environment

### 5.1 `production`

| 设置 | 值 |
|---|---|
| Deployment branches | `main` only |
| Required reviewers | **1-2 个** (你 + 联合创始人) |
| Wait timer | 0 分钟 |
| Environment secrets | (见 4.2,全部) |

### 5.2 `staging`

| 设置 | 值 |
|---|---|
| Deployment branches | `develop`, `release/*` |
| Required reviewers | 0 (自动) |
| Environment secrets | (用 staging 域名,例: `staging-api.yefzyj.top`) |

### 5.3 `preview` (PR 触发,自动)

GitHub Actions 自动创建,无需配置。

---

## 🪝 6. Webhooks

**位置**: Settings → Webhooks → Add webhook

### 6.1 部署通知 (推荐)

| 项 | 值 |
|---|---|
| Payload URL | (服务器上跑的 webhook relay,如 `https://yefzyj.top/hooks/deploy`) |
| Content type | `application/json` |
| Secret | (随机 32 字节) |
| Events | ☑ Push / ☑ Pull request / ☑ Release |
| Active | ✅ |

### 6.2 飞书 / Slack 通知(可选)

类似上面,Payload URL 指向飞书机器人 webhook。

---

## 🏷️ 7. Issue Labels (推荐完整套)

**位置**: Issues → Labels

### 7.1 类型
- `bug` (#d73a4a 红) — Something isn't working
- `enhancement` (#a2eeef 蓝) — New feature or request
- `documentation` (#0075ca 蓝) — Improvements or additions to docs
- `performance` (#fbca04 黄) — Performance issue
- `security` (#b60205 红) — Security issue

### 7.2 优先级
- `priority/P0` (#b60205 红) — Blocker
- `priority/P1` (#d93f0b 橙) — High
- `priority/P2` (#fbca04 黄) — Medium
- `priority/P3` (#0e8a16 绿) — Low

### 7.3 区域
- `area/backend` (#5319e7 紫) — FastAPI / Python
- `area/web` (#1d76db 蓝) — Next.js / TypeScript
- `area/ios` (#c5def5 浅蓝) — Swift (Phase 7B)
- `area/ci` (#bfd4f2 灰) — GitHub Actions
- `area/docs` (#d4c5f9 浅紫) — Documentation
- `area/rct` (#fef2c0 黄) — 真实 RCT 试验

### 7.4 状态
- `status/blocked` (#b60205) — Cannot proceed
- `status/in-progress` (#fbca04) — Currently being worked
- `status/needs-review` (#0e8a16) — Awaiting review
- `status/good-first-issue` (#7057ff) — Beginner friendly

### 7.5 特殊
- `wontfix` (#ffffff 白) — This will not be worked on
- `duplicate` (#cccccc 灰) — Already exists
- `wip` (#ededed 灰) — Work in progress

---

## 🛡️ 8. 安全 (Security tab)

**位置**: Settings → Code security and analysis

### 8.1 立即开启

- ☑ **Dependabot alerts** (依赖漏洞告警)
- ☑ **Dependabot security updates** (自动 PR 修复)
- ☑ **Secret scanning** (检测 commit 里的密钥)
- ☑ **Push protection** (阻止 push 含密钥)

### 8.2 推荐开启

- ☑ **Code scanning (CodeQL)** (代码静态分析)
  - 语言: Python + JavaScript/TypeScript
  - Query suite: security-extended + quality

### 8.3 高级 (付费)

- GitHub Advanced Security (企业版才需要)
- Private vulnerability disclosure (HackerOne 集成)

### 8.4 已就绪

- ✅ `SECURITY.md` (有,见仓库根)
- ✅ `.github/ISSUE_TEMPLATE/bug_report.md` (有)
- ✅ Default branch protection (待开启,见 §2)

---

## 🔄 9. CI/CD 配置

**位置**: Settings → Actions → General

### 9.1 通用

| 设置 | 值 |
|---|---|
| Actions permissions | **Allow all actions and reusable workflows** |
| Workflow permissions | **Read and write permissions** (需要 OIDC deploy 的话) |
| Allow GitHub Actions to create and approve pull requests | ✅ |

### 9.2 当前 workflow 文件

```
.github/workflows/ci.yml    (3 jobs: backend / web / scripts)
```

后续可加:
- `.github/workflows/deploy.yml` (deploy to yefzyj.top on tag)
- `.github/workflows/release.yml` (auto gen changelog)
- `.github/workflows/dependabot-auto-merge.yml`
- `.github/workflows/codeql.yml`

### 9.3 Runner

- 默认: `ubuntu-latest`
- 特殊需求: 4090 GPU runner (如需本地 LLM 测试) → 需 GitHub Team plan

---

## 📊 10. Insights & 监控

**位置**: Insights 标签

| 页面 | 用途 |
|---|---|
| **Pulse** | 每周/每月 commit / PR / issue 统计 |
| **Contributors** | 贡献者排行 (用于奖励/署名) |
| **Community** | 标准健康度报告 |
| **Traffic** | 访客 / 克隆 / 引用统计 |
| **Dependencies** | Dependabot 检测的依赖图 |
| **Forks** | Fork 列表 |
| **Code frequency** | commit 历史曲线 |

---

## 🏷️ 11. Releases (发版)

### 11.1 Tag 命名规范

```
vMAJOR.MINOR.PATCH
例: v4.0.0, v4.1.0, v4.0.1
```

### 11.2 发版流程

```bash
# 打 tag
git tag -a v4.0.0 -m "v4.0 - 营销站 + Web App + Web MIDI"
git push origin v4.0.0

# 在 GitHub 创建 Release
# → https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano/releases/new
# → 选择 tag + 标题 + 自动生成 notes + 发布
```

### 11.3 自动化(后续)

加 `.github/workflows/release.yml`:
- 检测 `v*` tag → 自动 build + create release
- 自动从 commit message 生成 changelog
- 自动发 Docker image 到 ghcr.io

---

## 🧰 12. 常用管理员操作速查 (curl / API)

> **前提**: 用 GitHub CLI `gh` (推荐) 或 PAT + curl

### 12.1 安装 gh CLI (macOS)

```bash
brew install gh
gh auth login --with-token  # 用 1Password 的 token
```

### 12.2 常用命令

```bash
# 看仓库状态
gh repo view YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano --web

# 改 description / topics
gh repo edit YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano \
  --description "AI classical piano coach — 5-dim evaluation + 7-day adaptive curriculum + RCT d=1.34" \
  --add-topic ai,music,piano,education,web-midi,fastapi,nextjs

# 列 open issues
gh issue list --repo YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano

# 创建 issue
gh issue create --title "..." --body "..." --label "bug,area/web"

# 加 collaborator
gh api -X PUT /repos/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano/collaborators/{username} \
  -f permission=push

# 创建 label
gh label create "area/ios" --color "c5def5" --description "iOS Swift app"

# 启用 Dependabot
gh api -X PUT /repos/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano/vulnerability-alerts

# 触发 workflow
gh workflow run ci.yml --ref main
```

### 12.3 紧急操作: 锁仓

```bash
# 锁 issues (spam 风暴)
gh repo edit YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano --enable-issues=false
# archive
gh repo archive YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano
# transfer
gh repo transfer YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano NEW_OWNER
# delete
gh repo delete YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano --yes
```

---

## 📞 13. 关键 URL 一览

| 用途 | URL |
|---|---|
| 仓库主页 | https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano |
| Settings | https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano/settings |
| Branches | https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano/settings/branches |
| Secrets | https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano/settings/secrets |
| Environments | https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano/settings/environments |
| Webhooks | https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano/settings/hooks |
| Security | https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano/settings/security_analysis |
| Actions | https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano/actions |
| Insights | https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano/pulse |
| Releases | https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano/releases |
| New Issue | https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano/issues/new |
| New PR | https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano/compare |
| PAT 管理 | https://github.com/settings/tokens |
| OAuth Apps | https://github.com/settings/connections/applications |

---

## ✅ 14. 立即执行清单 (按优先级)

### 🔴 P0 (今天做)
1. **撤销旧 token** `ghp_…REDACTED…` (曾经在 chat history 暴露) + 生成新 token
2. 配 main 分支保护 (PR + 1 approval + status checks)
3. 加 `.github/CODEOWNERS`
4. 开启 Dependabot + Secret scanning + Push protection

### 🟡 P1 (本周做)
5. 配 4 个 CI Secrets (DATABASE_URL / REDIS_URL / JWT_SECRET / NEXTAUTH_SECRET)
6. 创建 `production` environment + 1-2 个 required reviewers
7. 补 Topics: ai, music, piano, education, web-midi, fastapi, nextjs, postgresql
8. 改 Description 为更专业的版本
9. 加完整套 Issue labels (§7)
10. 创建 v4.0 Release + tag

### 🟢 P2 (下月做)
11. 配 deploy workflow (`.github/workflows/deploy.yml`)
12. 配 CodeQL
13. 集成 Codecov 覆盖率徽章
14. 配 Slack 告警
15. 启用 GitHub Pages 文档站

---

## 📊 15. 当前状态总览

| 维度 | 状态 |
|---|---|
| Repo 存在 | ✅ |
| Admin 权限 | ✅ |
| 默认分支 main | ✅ |
| 公开访问 | ✅ |
| 描述 | ✅ (你的浪漫版) |
| Topics | ❌ 空 |
| 分支保护 | ❌ 未开 |
| Secrets | ❌ 0 个 |
| Environments | ❌ 未创建 |
| Dependabot | ❌ 未开 |
| Secret scanning | ❌ 未开 |
| CI 已跑过 | ❌ 还没 (没 secrets) |
| Releases | ❌ 0 个 |
| Issues | 0 open |
| Stars / Forks | 0 / 0 |

---

**生成时间**: 2026-07-27
**适用版本**: CoPiano v4.0 (Cycle 62)
**维护者**: Mavis (cron-driven)
