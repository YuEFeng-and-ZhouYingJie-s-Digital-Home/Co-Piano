import NextAuth from 'next-auth';
import Credentials from 'next-auth/providers/credentials';
import Google from 'next-auth/providers/google';
import Apple from 'next-auth/providers/apple';
import { authConfig } from './auth.config';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'https://api.yefzyj.top';

/**
 * NextAuth 主入口 — 包含 Credentials + OAuth2 providers
 * Credentials: 调后端 /api/v1/auth/login 拿 JWT
 * Apple/Google: 调后端 /api/v1/oauth/{apple|google}/callback 验证
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

    /**
     * Google OAuth2
     * ID token 由后端验证,我们传 access_token 给前端
     */
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          prompt: 'consent',
          access_type: 'offline',
          response_type: 'code',
        },
      },
    }),

    /**
     * Apple Sign In
     */
    Apple({
      clientId: process.env.APPLE_CLIENT_ID!,
      clientSecret: process.env.APPLE_CLIENT_SECRET!,
    }),
  ],
});
