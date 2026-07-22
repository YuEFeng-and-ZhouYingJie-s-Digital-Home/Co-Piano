import { redirect } from 'next/navigation';
import { auth } from '@/auth';
import { api, ApiError } from '@/lib/api';
import { Sidebar } from '@/components/app/sidebar';
import { MobileNav } from '@/components/app/mobile-nav';
import { UserMenu } from '@/components/app/user-menu';
import { SeniorModeApplier } from '@/components/app/senior-mode-applier';
import type { UserProfile } from '@/lib/settings-types';

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();

  if (!session?.user) {
    redirect('/login?callbackUrl=/app');
  }

  // 拉 user profile 拿 is_senior(失败 fallback false)
  let isSenior = false;
  try {
    const profile = await api.get<UserProfile>('/api/v1/users/me');
    isSenior = profile.is_senior;
  } catch (e) {
    if (!(e instanceof ApiError && e.status === 401)) {
      console.warn('Failed to load user profile for senior mode:', e);
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* 应用银发模式 className 到 <html> */}
      <SeniorModeApplier isSenior={isSenior} />

      {/* 桌面端 sidebar */}
      <Sidebar />

      {/* 主内容区 */}
      <div className="lg:pl-64">
        {/* 移动端 header (含 user menu) */}
        <MobileNav />

        {/* 桌面端 top bar (仅 user menu) */}
        <div className="hidden lg:flex sticky top-0 z-30 h-16 items-center justify-end border-b border-border bg-background/95 px-6 backdrop-blur">
          <UserMenu name={session.user.name} email={session.user.email} />
        </div>

        {/* 页面内容 */}
        <main className="px-4 py-6 pb-24 lg:px-8 lg:pb-8">{children}</main>
      </div>

      {/* 移动端固定 user menu (底部 tab bar 上方) */}
      <div className="fixed bottom-16 right-4 z-50 lg:hidden">
        <UserMenu name={session.user.name} email={session.user.email} />
      </div>
    </div>
  );
}
