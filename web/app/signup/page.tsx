import type { Metadata } from 'next';
import Link from 'next/link';
import { AuthShell } from '@/components/auth/auth-shell';
import { SignupForm } from '@/components/auth/signup-form';
import { OAuthButtons } from '@/components/auth/oauth-buttons';

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
