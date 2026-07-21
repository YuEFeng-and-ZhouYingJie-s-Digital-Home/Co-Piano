# CoPiano Web

> Next.js 14 marketing + web app for [copiano.com](https://copiano.com)

## Stack
- **Framework**: Next.js 14.2 (App Router, RSC)
- **Language**: TypeScript 5.6
- **Styling**: Tailwind CSS 3.4 + shadcn/ui patterns
- **Charts**: Recharts 2.12
- **Icons**: Lucide React
- **Node**: ≥18.17

## 目录结构

```
web/
├── app/                     # App Router
│   ├── layout.tsx           # 全局 layout (字体/SEO/主题)
│   ├── page.tsx             # / 营销首页
│   ├── globals.css          # Tailwind + 钢琴主题 CSS 变量
│   ├── pricing/             # /pricing
│   ├── about/               # /about
│   └── sitemap.ts           # SEO sitemap
├── components/
│   ├── ui/                  # shadcn/ui 组件 (Button, Card, ...)
│   ├── marketing/           # 营销页组件
│   └── webapp/              # 登录后组件
├── lib/
│   ├── utils.ts             # cn() + formatters
│   └── api.ts               # 后端 API client
├── public/                  # 静态资源
├── tailwind.config.ts
├── next.config.mjs
├── tsconfig.json
└── package.json
```

## 快速开始

```bash
# 安装依赖 (需要 Node 18.17+)
npm install
# 或: pnpm install / bun install

# 开发
npm run dev          # http://localhost:3000

# 生产构建
npm run build
npm start            # http://localhost:3000

# Lint + 类型检查
npm run lint
npm run type-check

# 单元测试
npm test
```

## 环境变量

复制 `.env.example` → `.env.local`,填入实际值。

| 变量 | 说明 |
| --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | 后端 API 基础 URL (如 `https://api.copiano.com`) |
| `NEXT_PUBLIC_WS_BASE_URL` | WebSocket 基础 URL (如 `wss://api.copiano.com`) |
| `NEXT_PUBLIC_APP_URL` | Web App URL (`https://app.copiano.com`) |
| `STRIPE_SECRET_KEY` | Stripe 订阅密钥 (服务端) |

## 部署

详见 `docs/deploy_web.md` (后续 A5.7 添加)。
- 静态导出:`next build` → `.next/standalone`
- Nginx 反代 + Let's Encrypt SSL
- 5 子域名:apex (营销) / app / admin / docs / api

## 当前进度

- [x] **A5.1** Next.js 14 项目初始化 (本轮)
- [ ] **A5.2** Tailwind + shadcn/ui 配置
- [ ] **A5.3** Marketing 主页 (Hero + 5 维 + RCT 数据)
- [ ] **A5.4** /pricing 订阅页
- [ ] **A5.5** /about 团队/论文
- [ ] **A5.6** SEO meta + sitemap.xml
- [ ] **A5.7** 部署到 copiano.com (Nginx 静态)
