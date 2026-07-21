import { auth } from '@/auth';
import { api, ApiError } from '@/lib/api';
import { CurriculumWeekView } from '@/components/curriculum/curriculum-week';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import type { CurriculumWeek } from '@/lib/curriculum-types';

export const metadata = { title: '课程' };

export default async function CurriculumPage() {
  const session = await auth();
  if (!session?.accessToken) {
    return <div>请先登录</div>;
  }

  let week: CurriculumWeek | null = null;
  let error: string | null = null;

  try {
    week = await api.get<CurriculumWeek>('/api/v1/curriculum');
  } catch (e) {
    if (e instanceof ApiError) {
      error = e.detail;
    } else {
      error = '无法加载课程';
    }
  }

  if (error || !week) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">我的课程</h1>
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">
              {error ?? '还没有课程数据'}
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              完成第一次录音评估后,系统会为你生成 7 天自适应课程。
            </p>
            <Button asChild variant="piano" className="mt-4">
              <Link href="/app/record">开始第一次录音</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">我的课程</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          7 天自适应课程 · SM-2 间隔重复 · 每日 30-60 分钟
        </p>
      </div>
      <CurriculumWeekView week={week} />
    </div>
  );
}
