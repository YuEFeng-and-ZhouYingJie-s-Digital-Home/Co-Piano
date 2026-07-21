import type { NextAuthConfig } from 'next-auth';

/**
 * Edge-safe auth 配置 — 用于 middleware.ts
 * 不包含任何 Node-only 的 callback (如 db lookup)
 *
 * Credentials/OAuth providers 在 auth.ts 中添加
 */
export const authConfig: NextAuthConfig = {
  pages: {
    signIn: '/login',
    newUser: '/signup',
    error: '/login',
  },
  session: { strategy: 'jwt' },
  callbacks: {
    /**
     * 路由保护: middleware 调用
     * 受保护路径: /app/* 需要登录
     */
    authorized({ auth, request: { nextUrl } }) {
      const isLoggedIn = !!auth?.user;
      const isOnApp = nextUrl.pathname.startsWith('/app');

      if (isOnApp) {
        if (isLoggedIn) return true;
        // 未登录跳到 /login?redirect=<原 URL>
        return false;
      }

      // 已登录访问 /login 或 /signup 跳到 /app
      if (isLoggedIn && (nextUrl.pathname === '/login' || nextUrl.pathname === '/signup')) {
        return Response.redirect(new URL('/app', nextUrl));
      }

      return true;
    },
    /**
     * JWT 持久化: 把后端 access_token 放进 session
     */
    jwt({ token, user }) {
      if (user) {
        // 来自 authorize() 的 user object
        token.accessToken = (user as { accessToken?: string }).accessToken;
        token.refreshToken = (user as { refreshToken?: string }).refreshToken;
        token.userId = (user as { id?: string }).id;
      }
      return token;
    },
    /**
     * Session 暴露给客户端的字段
     */
    session({ session, token }) {
      if (token) {
        (session as { accessToken?: string }).accessToken = token.accessToken as string | undefined;
        (session as { refreshToken?: string }).refreshToken = token.refreshToken as string | undefined;
        (session.user as { id?: string }).id = token.userId as string | undefined;
      }
      return session;
    },
  },
  providers: [], // 在 auth.ts 中添加
};
