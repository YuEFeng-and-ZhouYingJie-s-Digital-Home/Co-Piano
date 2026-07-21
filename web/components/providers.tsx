'use client';

import { SessionProvider } from 'next-auth/react';

/**
 * 客户端 Provider 包装 — SessionProvider 给 useSession() 用
 */
export function Providers({ children }: { children: React.ReactNode }) {
  return <SessionProvider>{children}</SessionProvider>;
}
