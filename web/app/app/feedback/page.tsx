import { auth } from '@/auth';
import { api, ApiError } from '@/lib/api';
import { FeedbackList } from '@/components/feedback/feedback-list';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { Mic } from 'lucide-react';
import type { FeedbackListItem } from '@/lib/feedback-types';

export const metadata = { title: '反馈历史' };

export default async function FeedbackPage() {
  const session = await auth();
  if (!session?.accessToken) return null;

  let items: FeedbackListItem[] = [];
  let error: string | null = null;

  try {
    items = await api.get<FeedbackListItem[]>('/api/v1/feedback');
  } catch (e) {
    error = e instanceof ApiError ? e.detail : '无法加载历史';
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">反馈历史</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            所有评估记录 · 点击查看 LLM 个性化反馈
          </p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href="/app/record">
            <Mic className="mr-1.5 h-3.5 w-3.5" />
            新录音
          </Link>
        </Button>
      </div>

      {error ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            {error}
          </CardContent>
        </Card>
      ) : (
        <FeedbackList items={items} />
      )}
    </div>
  );
}
