'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { Check, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface CompleteBlockButtonProps {
  blockId: string;
  completed: boolean;
  /** 0-100 (SM-2 评分);可选,未传则用 80 (默认掌握) */
  score?: number;
}

export function CompleteBlockButton({
  blockId,
  completed,
  score,
}: CompleteBlockButtonProps) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const onClick = async () => {
    if (completed || pending) return;
    setError(null);
    startTransition(async () => {
      try {
        await api.post(
          `/api/v1/curriculum/blocks/${blockId}/complete`,
          { score: score ?? 80 },
        );
        router.refresh();
      } catch (err) {
        const msg =
          err && typeof err === 'object' && 'detail' in err
            ? String((err as { detail: unknown }).detail)
            : '提交失败';
        setError(msg);
      }
    });
  };

  return (
    <div className="flex flex-col items-end gap-1">
      <Button
        type="button"
        size="sm"
        variant={completed ? 'outline' : 'piano'}
        onClick={onClick}
        disabled={completed || pending}
        className={cn(completed && 'text-green-600 border-green-500/40')}
      >
        {pending ? (
          <Loader2 className="mr-1 h-3 w-3 animate-spin" />
        ) : completed ? (
          <Check className="mr-1 h-3 w-3" />
        ) : null}
        {completed ? '已完成' : '标记完成'}
      </Button>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
