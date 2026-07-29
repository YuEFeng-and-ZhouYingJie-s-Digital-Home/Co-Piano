import NextAuth from 'next-auth';
import Credentials from 'next-auth/providers/credentials';
import { authConfig } from './auth.config';
import { apiBaseUrl } from './lib/urls';

const API_BASE_URL = apiBaseUrl();

/**
 * NextAuth 主入口 — 目前只支持邮箱 + 密码登录
 * OAuth (Google/Apple) 暂未启用,等配置好 client_id/secret + 后端用户打通后再加
 */
export const { handlers, signIn, signOut, auth } = NextAuth({
  ...authConfig,
  providers: [
    /**
     * 邮箱 + 密码登录
     * 实际验证在后端 (bcrypt 3.2.2 + JWT)
     * 前端只做表单收集 + JWT 透传
     */
    Credentials({
      name: 'credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        const email = credentials?.email as string | undefined;
        const password = credentials?.password as string | undefined;
        if (!email || !password) return null;

        try {
          const res = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
          });

          if (!res.ok) {
            return null;
          }

          const data = (await res.json()) as {
            access_token: string;
            refresh_token: string;
            user: { id: string; email: string; name?: string };
          };

          return {
            id: data.user.id,
            email: data.user.email,
            name: data.user.name,
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
          };
        } catch (err) {
          console.error('[auth] login fetch failed:', err);
          return null;
        }
      },
    }),
  ],
});
