import type { Metadata } from 'next';
import Link from 'next/link';
import { AuthShell } from '@/components/auth/auth-shell';
import { LoginForm } from '@/components/auth/login-form';
import { OAuthButtons } from '@/components/auth/oauth-buttons';

export const metadata: Metadata = {
  title: '登录',
  description: '登录 CoPiano 继续你的钢琴学习',
  robots: { index: false, follow: false },
};

export default function LoginPage() {
  return (
    <AuthShell
      title="欢迎回来"
      subtitle="继续你的钢琴学习之旅"
      footer={
        <>
          还没账号?{' '}
          <Link href="/signup" className="font-medium text-piano-500 hover:underline">
            免费注册
          </Link>
        </>
      }
    >
      <LoginForm />

      <div className="relative my-6">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-card px-2 text-muted-foreground">或</span>
        </div>
      </div>

      <OAuthButtons />
    </AuthShell>
  );
}
