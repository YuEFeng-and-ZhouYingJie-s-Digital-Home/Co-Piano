import NextAuth from 'next-auth';
import { authConfig } from './auth.config';

// Edge-safe middleware — 不 import 任何 Node-only 模块
const { auth } = NextAuth(authConfig);

export default auth((req) => {
  // authorized callback 已在 authConfig 中处理路由保护
  // 这里可以加日志 / 额外 headers
  const response = req.auth;
  if (response?.user) {
    console.log(`[auth] ${req.nextUrl.pathname} by ${response.user.email}`);
  }
});

export const config = {
  matcher: [
    /*
     * 匹配所有路径除了:
     * - api/auth/* (NextAuth 内部)
     * - api/health (健康检查)
     * - _next/static, _next/image (Next.js 静态)
     * - favicon.ico, manifest.webmanifest, sitemap.xml, robots.txt
     * - opengraph-image, twitter-image, icon, apple-icon (动态 OG)
     * - public 下的 .svg/.png/.jpg/.jpeg/.ico/.webp
     */
    '/((?!api/auth|api/health|_next/static|_next/image|favicon.ico|manifest.webmanifest|sitemap.xml|robots.txt|opengraph-image|twitter-image|apple-icon|icon|.*\\.(?:svg|png|jpg|jpeg|ico|webp)$).*)',
  ],
};
