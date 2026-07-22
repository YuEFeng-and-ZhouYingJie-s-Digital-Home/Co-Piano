'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Crown, Calendar, ArrowRight, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { PLAN_META, type Plan, type UserProfile } from '@/lib/settings-types';
import { api, ApiError } from '@/lib/api';
import { formatDate } from '@/lib/utils';

interface SubscriptionCardProps {
  profile: UserProfile;
}

export function SubscriptionCard({ profile }: SubscriptionCardProps) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const meta = PLAN_META[profile.plan];
  const isFree = profile.plan === 'free';

  const manageBilling = () => {
    // 实际: 调后端创建 Stripe customer portal session
    // 这里直接跳 /pricing
    router.push('/pricing');
  };

  const cancel = () => {
    if (!confirm('确定要取消订阅吗?当前周期结束后将降级为 Free。')) return;
    startTransition(async () => {
      try {
        await api.post('/api/v1/users/me/cancel-subscription');
        router.refresh();
      } catch (e) {
        setError(e instanceof ApiError ? e.detail : '取消失败');
      }
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Crown className="h-4 w-4 text-piano-500" />
          订阅
        </CardTitle>
        <CardDescription>当前方案与账单</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-2xl">{meta.emoji}</span>
              <span className={`text-lg font-semibold ${meta.color}`}>
                {meta.label}
              </span>
            </div>
            {profile.plan_expires_at && (
              <div className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                <Calendar className="h-3 w-3" />
                到期 {formatDate(profile.plan_expires_at)}
              </div>
            )}
          </div>
          <div className="flex gap-2">
            {isFree ? (
              <Button asChild variant="piano">
                <Link href="/pricing">
                  升级方案
                  <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
                </Link>
              </Button>
            ) : (
              <>
                <Button variant="outline" onClick={manageBilling}>
                  管理订阅
                </Button>
                <Button
                  variant="ghost"
                  onClick={cancel}
                  disabled={pending}
                  className="text-destructive hover:text-destructive"
                >
                  {pending && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
                  取消订阅
                </Button>
              </>
            )}
          </div>
        </div>

        {error && (
          <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        )}

        {/* 方案对比 */}
        <div className="border-t border-border pt-3">
          <p className="text-xs text-muted-foreground mb-2">方案对比</p>
          <ul className="space-y-1 text-sm">
            <PlanFeature plan="free" current={profile.plan} label="Free: 3 次/天录音, 7 天课程" />
            <PlanFeature plan="pro" current={profile.plan} label="Pro: 无限录音 + 90 天课程 + LLM 反馈 (¥29/月)" />
            <PlanFeature plan="senior" current={profile.plan} label="银发: Pro 全部免费 (60+ 公益)" />
            <PlanFeature plan="teacher" current={profile.plan} label="Teacher: 30 学生班级 (¥99/月)" />
            <PlanFeature plan="school" current={profile.plan} label="School: 私有部署 + SLA (¥999/月)" />
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}

function PlanFeature({
  plan,
  current,
  label,
}: {
  plan: Plan;
  current: Plan;
  label: string;
}) {
  const isCurrent = plan === current;
  return (
    <li className="flex items-center gap-2">
      {isCurrent ? (
        <Badge variant="piano" className="text-[10px]">当前</Badge>
      ) : (
        <span className="inline-block h-4 w-4" />
      )}
      <span className={isCurrent ? 'font-medium' : 'text-muted-foreground'}>
        {label}
      </span>
    </li>
  );
}
