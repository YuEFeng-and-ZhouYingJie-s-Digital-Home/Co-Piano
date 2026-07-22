'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { Play, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { api, ApiError } from '@/lib/api';
import {
  LEVEL_META,
  MODE_META,
  type SightReadingLevel,
  type SightReadingMode,
  type SightReadingSession,
} from '@/lib/sight-reading-types';

const LEVELS: SightReadingLevel[] = [1, 2, 3, 4];
const MODES: SightReadingMode[] = ['staff', 'numbered', 'dual'];

export function SightReadingStarter() {
  const router = useRouter();
  const [level, setLevel] = useState<SightReadingLevel>(1);
  const [mode, setMode] = useState<SightReadingMode>('staff');
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const start = () => {
    setError(null);
    startTransition(async () => {
      try {
        const session = await api.post<SightReadingSession>(
          '/api/v1/sight-reading/session',
          { level, mode },
        );
        router.push(`/app/sight-reading/session/${session.id}`);
      } catch (e) {
        setError(e instanceof ApiError ? e.detail : '无法开始训练');
      }
    });
  };

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">视奏训练</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          4 难度 × 3 模式 · 20 题/轮 · 即时反馈
        </p>
      </div>

      {/* 难度 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">难度</CardTitle>
          <CardDescription>选一个适合你的难度</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {LEVELS.map((lvl) => {
              const meta = LEVEL_META[lvl];
              const active = level === lvl;
              return (
                <button
                  key={lvl}
                  type="button"
                  onClick={() => setLevel(lvl)}
                  className={cn(
                    'rounded-lg border-2 p-4 text-left transition-all',
                    active
                      ? 'border-piano-500 bg-piano-500/10'
                      : 'border-border hover:border-piano-500/50',
                  )}
                >
                  <div className="text-3xl">{meta.emoji}</div>
                  <div className="mt-2 font-semibold flex items-center gap-2">
                    L{lvl} {meta.label}
                    {active && <Badge variant="piano" className="text-[10px]">已选</Badge>}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {meta.description}
                  </p>
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* 模式 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">显示模式</CardTitle>
          <CardDescription>看哪种谱面</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-3">
            {MODES.map((m) => {
              const meta = MODE_META[m];
              const active = mode === m;
              return (
                <button
                  key={m}
                  type="button"
                  onClick={() => setMode(m)}
                  className={cn(
                    'rounded-lg border-2 p-4 text-left transition-all',
                    active
                      ? 'border-piano-500 bg-piano-500/10'
                      : 'border-border hover:border-piano-500/50',
                  )}
                >
                  <div className="text-3xl">{meta.emoji}</div>
                  <div className="mt-2 font-semibold">{meta.label}</div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {meta.description}
                  </p>
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      <Button
        onClick={start}
        disabled={pending}
        variant="piano"
        size="lg"
        className="w-full"
      >
        {pending ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            正在准备 20 题...
          </>
        ) : (
          <>
            <Play className="mr-2 h-4 w-4" />
            开始训练 (L{level} {LEVEL_META[level].label} · {MODE_META[mode].label})
          </>
        )}
      </Button>
    </div>
  );
}
