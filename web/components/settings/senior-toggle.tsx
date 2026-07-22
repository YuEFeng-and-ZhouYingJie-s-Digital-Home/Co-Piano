'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { Heart, Loader2, Info } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { api, ApiError } from '@/lib/api';

interface SeniorToggleProps {
  initial: boolean;
}

export function SeniorToggle({ initial }: SeniorToggleProps) {
  const router = useRouter();
  const [enabled, setEnabled] = useState(initial);
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const onToggle = () => {
    setError(null);
    const next = !enabled;
    setEnabled(next);
    startTransition(async () => {
      try {
        await api.patch('/api/v1/users/me', { is_senior: next });
        router.refresh();
      } catch (e) {
        setError(e instanceof ApiError ? e.detail : '切换失败');
        setEnabled(!next); // 回滚
      }
    });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Heart className="h-4 w-4 text-pink-500" />
              银发模式
            </CardTitle>
            <CardDescription>大字体 + 简化术语 + 慢节奏教学</CardDescription>
          </div>
          {enabled && (
            <Badge variant="piano">
              <Heart className="mr-1 h-3 w-3" />
              已开启
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="rounded-md bg-pink-500/5 border border-pink-500/20 p-3 flex items-start gap-2 text-sm">
          <Info className="h-4 w-4 text-pink-500 flex-shrink-0 mt-0.5" />
          <div className="text-muted-foreground">
            60+ 岁长者开启后将自动获得 <strong>Pro 全功能免费</strong>,
            简化 UI,术语自动翻译 (terminus → 渐慢)。
            我们不验证年龄,请尊重这份公益资源。
          </div>
        </div>

        {error && (
          <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        )}

        <Button
          onClick={onToggle}
          disabled={pending}
          variant={enabled ? 'outline' : 'piano'}
        >
          {pending && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
          {enabled ? '关闭银发模式' : '开启银发模式'}
        </Button>
      </CardContent>
    </Card>
  );
}
