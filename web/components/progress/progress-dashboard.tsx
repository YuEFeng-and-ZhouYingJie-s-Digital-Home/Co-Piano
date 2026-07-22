'use client';

import { useMemo, useState } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { DimensionTrendChart } from '@/components/progress/dimension-trend-chart';
import { RangeSelector } from '@/components/progress/range-selector';
import {
  filterByRange,
  summarize,
  type ProgressPoint,
  type RangeKey,
} from '@/lib/progress-types';
import { DIMENSION_META } from '@/lib/evaluation-types';

interface ProgressDashboardProps {
  allPoints: ProgressPoint[];
}

export function ProgressDashboard({ allPoints }: ProgressDashboardProps) {
  const [range, setRange] = useState<RangeKey>('30d');

  const points = useMemo(() => filterByRange(allPoints, range), [allPoints, range]);
  const summary = useMemo(() => summarize(points), [points]);

  if (allPoints.length === 0) {
    return <EmptyState />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">进度曲线</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            5 维成长轨迹 · 共 {allPoints.length} 次评估
          </p>
        </div>
        <RangeSelector value={range} onChange={setRange} />
      </div>

      <DimensionTrendChart points={points} />

      <div>
        <h2 className="text-lg font-semibold mb-3">维度摘要</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {summary.map((s) => {
            const meta = DIMENSION_META[s.dimension];
            const TrendIcon =
              s.delta > 1 ? TrendingUp : s.delta < -1 ? TrendingDown : Minus;
            const trendColor =
                s.delta > 1
                  ? 'text-green-500'
                  : s.delta < -1
                    ? 'text-red-500'
                    : 'text-muted-foreground';
            return (
              <Card key={s.dimension}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-2xl">{meta.emoji}</span>
                    <Badge variant="outline" className="text-[10px] font-mono">
                      权重 {Math.round(meta.weight * 100)}%
                    </Badge>
                  </div>
                  <div className="text-sm text-muted-foreground">{meta.label}</div>
                  <div className="mt-1 text-3xl font-bold tabular-nums">
                    {s.latest}
                  </div>
                  <div className="mt-2 flex items-center gap-2 text-xs">
                    <span className={`flex items-center gap-0.5 ${trendColor}`}>
                      <TrendIcon className="h-3 w-3" />
                      {s.delta > 0 ? '+' : ''}
                      {s.delta}
                    </span>
                    <span className="text-muted-foreground">
                      · 峰值 {s.peak} · 均 {s.avg}
                    </span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>进度曲线</CardTitle>
        <CardDescription>还没有评估数据</CardDescription>
      </CardHeader>
      <CardContent className="py-12 text-center">
        <p className="text-muted-foreground">
          完成至少 1 次录音评估后,这里会显示 5 维成长曲线。
        </p>
      </CardContent>
    </Card>
  );
}
