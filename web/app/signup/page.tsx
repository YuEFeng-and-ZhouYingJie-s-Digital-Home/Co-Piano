import type { Metadata } from 'next';
import Link from 'next/link';
import { AuthShell } from '@/components/auth/auth-shell';
import { SignupForm } from '@/components/auth/signup-form';

export const metadata: Metadata = {
  title: '免费注册',
  description: '免费注册 CoPiano,开始 AI 钢琴学习',
  robots: { index: false, follow: false },
};

export default function SignupPage() {
  return (
    <AuthShell
      title="创建账号"
      subtitle="免费开始 7 天 Pro 试用 · 无需信用卡"
      footer={
        <>
          已有账号?{' '}
          <Link href="/login" className="font-medium text-piano-500 hover:underline">
            登录
          </Link>
        </>
      }
    >
      <SignupForm />
    </AuthShell>
  );
}
