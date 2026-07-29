'use client';

import { useSession, signIn, signOut } from 'next-auth/react';

/**
 * 客户端 auth helpers — 包装 next-auth/react
 * OAuth (Google/Apple) 暂未启用,等配置好 client_id/secret + 后端用户打通后再加
 */

export function useAuth() {
  const { data: session, status } = useSession();
  return {
    user: session?.user ?? null,
    accessToken: session?.accessToken ?? null,
    isLoggedIn: status === 'authenticated',
    isLoading: status === 'loading',
  };
}

export async function loginWithCredentials(email: string, password: string) {
  return signIn('credentials', {
    email,
    password,
    redirect: false,
  });
}

export async function logout() {
  return signOut({ callbackUrl: '/' });
}
