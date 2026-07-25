import { auth } from '@/auth';
import { api, ApiError } from '@/lib/api';
import { ProfileForm } from '@/components/settings/profile-form';
import { SeniorToggle } from '@/components/settings/senior-toggle';
import { SubscriptionCard } from '@/components/settings/subscription-card';
import { ChangePasswordForm } from '@/components/settings/change-password-form';
import { Card, CardContent } from '@/components/ui/card';
import { formatDate } from '@/lib/utils';
import type { UserProfile } from '@/lib/settings-types';

export const metadata = { title: '设置' };

export default async function SettingsPage() {
  const session = await auth();
  if (!session?.accessToken) return null;

  let profile: UserProfile | null = null;
  let error: string | null = null;
  try {
    profile = await api.get<UserProfile>('/api/v1/users/me');
  } catch (e) {
    error = e instanceof ApiError ? e.detail : '无法加载资料';
  }

  if (error || !profile) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-sm text-muted-foreground">
          {error ?? '加载失败'}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">设置</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          账户 · 银发模式 · 订阅 · 安全
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          注册于 {formatDate(profile.created_at)}
        </p>
      </div>

      <ProfileForm initial={{ name: profile.name, email: profile.email }} />

      <SeniorToggle initial={profile.is_senior} />

      <div id="subscription">
        <SubscriptionCard profile={profile} />
      </div>

      <ChangePasswordForm />

      <div className="text-center text-xs text-muted-foreground pt-4">
        需要帮助?联系{' '}
        <a href="mailto:hi@yefzyj.top" className="underline">
          hi@yefzyj.top
        </a>
      </div>
    </div>
  );
}
