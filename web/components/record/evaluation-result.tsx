'use client';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Sparkles } from 'lucide-react';
import {
  DIMENSIONS_ORDER,
  DIMENSION_META,
  type Evaluation,
} from '@/lib/evaluation-types';
import { cn } from '@/lib/utils';

interface EvaluationResultProps {
  evaluation: Evaluation;
}

export function EvaluationResult({ evaluation }: EvaluationResultProps) {
  const overall = Math.round(evaluation.overall);
  const level =
    overall >= 90 ? '大师'
      : overall >= 75 ? '熟练'
        : overall >= 60 ? '进阶'
          : overall >= 40 ? '入门'
            : '初学';
  const levelVariant = overall >= 75 ? 'success' : overall >= 60 ? 'piano' : 'outline';

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>5 维 AI 评估结果</CardTitle>
            <CardDescription>
              模型 {evaluation.model_version} · 评估耗时 {evaluation.latency_ms}ms
            </CardDescription>
          </div>
          <Badge variant={levelVariant as 'success' | 'piano' | 'outline'} className="text-sm">
            {level}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* 总分大字 */}
        <div className="text-center py-4">
          <div className="text-6xl font-bold text-piano-500 tabular-nums">
            {overall}
          </div>
          <div className="mt-1 text-sm text-muted-foreground">综合分 (0-100)</div>
        </div>

        {/* 5 维分项 */}
        <div className="space-y-3">
          {DIMENSIONS_ORDER.map((dim) => {
            const score = evaluation.scores[dim];
            if (!score) return null;
            const meta = DIMENSION_META[dim];
            const value = Math.round(score.score);
            const colorClass = getBarColor(value);
            return (
              <div key={dim}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{meta.emoji}</span>
                    <span className="text-sm font-medium">{meta.label}</span>
                    <span className="text-xs text-muted-foreground">
                      (权重 {Math.round(meta.weight * 100)}%)
                    </span>
                  </div>
                  <span className={cn('text-sm font-semibold tabular-nums', meta.color)}>
                    {value}
                  </span>
                </div>
                <div className="h-2 rounded-full bg-muted overflow-hidden">
                  <div
                    className={cn('h-full transition-all', colorClass)}
                    style={{ width: `${value}%` }}
                  />
                </div>
                {score.feedback && (
                  <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                    {score.feedback}
                  </p>
                )}
              </div>
            );
          })}
        </div>

        {/* 提示 */}
        <div className="rounded-md bg-piano-500/5 border border-piano-500/20 p-3 flex items-start gap-2 text-sm">
          <Sparkles className="h-4 w-4 text-piano-500 flex-shrink-0 mt-0.5" />
          <div>
            想看更深入的 LLM 个性化反馈?前往
            <a href="/app/feedback" className="ml-1 text-piano-500 underline">
              反馈历史
            </a>
            获取流式 AI 教练解读。
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function getBarColor(score: number): string {
  if (score >= 85) return 'bg-green-500';
  if (score >= 70) return 'bg-piano-500';
  if (score >= 55) return 'bg-amber-500';
  return 'bg-red-500';
}
