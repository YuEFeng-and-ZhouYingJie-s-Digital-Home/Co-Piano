import type { Metadata } from 'next';
import Link from 'next/link';
import { AuthShell } from '@/components/auth/auth-shell';
import { LoginForm } from '@/components/auth/login-form';

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
    </AuthShell>
  );
}
