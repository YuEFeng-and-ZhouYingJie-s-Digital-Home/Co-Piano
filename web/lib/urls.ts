/**
 * Domain-agnostic URL helpers — CoPiano
 *
 * 设计原则:同一份 build,以下三种 host 都能跑,不用重 build:
 *   1. 本地 dev         — http://localhost:3000
 *   2. Cloudflare Tunnel — https://<random>.trycloudflare.com
 *   3. 自定义域名        — https://yefzyj.top / https://app.yefzyj.top
 *
 * 规则:
 *   - 同源 (Next.js :3000) 链接     → 相对路径 "/login"
 *   - 跨源 (FastAPI :8001) 链接     → env var (NEXT_PUBLIC_DOCS_URL)
 *   - 邮件                         → env var (NEXT_PUBLIC_CONTACT_EMAIL)
 *   - SEO canonical/sitemap/OG     → 服务端从 request headers 读 host
 *
 * 重要:不要在这里 hardcode 任何 host:port,只能 hardcode 路径片段
 */

// ─── 路径 ───────────────────────────────────────────

/** 把任意 path 规整成相对路径,确保以 / 开头 */
export function appPath(p: string): string {
  if (!p) return '/';
  return p.startsWith('/') ? p : `/${p}`;
}

function joinPath(base: string, sub: string): string {
  if (!sub) return base;
  if (sub.startsWith('/')) return `${base}${sub}`;
  return `${base}/${sub}`;
}

// ─── 跨源 URL (env 控制) ──────────────────────────

/** 文档链接 — FastAPI Swagger
 *  - 设置 NEXT_PUBLIC_DOCS_URL → 跨源绝对 URL
 *  - 未设置 → 相对路径 /docs (Next.js 同源,挂静态路由或 FastAPI 代理)
 */
export function docsUrl(subpath: string = ''): string {
  const base = (process.env.NEXT_PUBLIC_DOCS_URL ?? '').replace(/\/$/, '');
  if (!base) return appPath(joinPath('/docs', subpath));
  return joinPath(base, subpath);
}

/** API base URL (FastAPI :8001)
 *  - 必须显式设置 (与 Next.js 不同源)
 *  - 默认空 → 调用会立刻失败并暴露问题 (不再悄悄指向 yefzyj.top)
 */
export function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? '';
}

/** WebSocket base URL — 默认从 API base 派生 (http→ws, https→wss) */
export function wsBaseUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_WS_BASE_URL ?? '';
  if (explicit) return explicit;
  const api = apiBaseUrl();
  if (!api) return '';
  return api.replace(/^http/i, 'ws');
}

// ─── 邮件 ──────────────────────────────────────────

export function contactEmail(): string {
  return process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? 'hi@yefzyj.top';
}

export function pressEmail(): string {
  return process.env.NEXT_PUBLIC_PRESS_EMAIL ?? 'press@yefzyj.top';
}

export function contactMailto(subject: string = ''): string {
  const e = contactEmail();
  return subject ? `mailto:${e}?subject=${encodeURIComponent(subject)}` : `mailto:${e}`;
}

// ─── 站点 base URL (canonical / sitemap / OG) ──────

/** 从 host + proto 拼出 base URL。host 可能含端口 (localhost:3000) */
export function siteUrl(host: string | null | undefined, proto: string = 'https'): string {
  const h = (host ?? '').split(',')[0]?.trim();
  if (!h) {
    // 兜底:build-time env (用于 build 阶段 / 完全无 headers 场景)
    const envUrl = process.env.NEXT_PUBLIC_SITE_URL;
    if (envUrl) return envUrl.replace(/\/$/, '');
    return 'http://localhost:3000';
  }
  return `${proto}://${h}`;
}

/** 从 Next.js headers() 拿 host + proto,处理 x-forwarded-* (反向代理) */
export function hostFromHeaders(
  getHeader: (k: string) => string | null,
): { host: string; proto: string } {
  const host = (getHeader('x-forwarded-host') ?? getHeader('host') ?? '')
    .split(',')[0]
    ?.trim() ?? '';
  const proto = (getHeader('x-forwarded-proto') ?? 'https')
    .split(',')[0]
    ?.trim() ?? 'https';
  return { host, proto };
}

// ─── 便捷取 site URL (服务端组件直接 import 用) ────

/** 服务端组件用:从 next/headers 拿 host 后拼 siteUrl
 *  使用:
 *    import { headers } from 'next/headers';
 *    import { currentSiteUrl } from '@/lib/urls';
 *    const url = currentSiteUrl(headers());
 */
export function currentSiteUrl(h: Headers): string {
  const { host, proto } = hostFromHeaders((k) => h.get(k));
  return siteUrl(host, proto);
}
