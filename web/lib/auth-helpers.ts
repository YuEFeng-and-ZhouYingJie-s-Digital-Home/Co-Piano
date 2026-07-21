'use client';

import { useSession, signIn, signOut } from 'next-auth/react';

/**
 * 客户端 auth helpers — 包装 next-auth/react
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

export async function loginWithGoogle() {
  return signIn('google', { callbackUrl: '/app' });
}

export async function loginWithApple() {
  return signIn('apple', { callbackUrl: '/app' });
}

export async function logout() {
  return signOut({ callbackUrl: '/' });
}
