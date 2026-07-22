import Link from 'next/link';
import { MessageSquare, Mic, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { FeedbackListItem } from '@/lib/feedback-types';
import { formatDate } from '@/lib/utils';

interface FeedbackListProps {
  items: FeedbackListItem[];
}

export function FeedbackList({ items }: FeedbackListProps) {
  if (items.length === 0) {
    return <EmptyState />;
  }

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <Link
          key={item.evaluation_id}
          href={`/app/feedback/${item.evaluation_id}`}
          className="block"
        >
          <Card className="transition-all hover:shadow-md hover:-translate-y-0.5 cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                {/* 总分大字 */}
                <div className="flex-shrink-0 text-center">
                  <div
                    className={`text-3xl font-bold tabular-nums ${getScoreColor(item.overall)}`}
                  >
                    {Math.round(item.overall)}
                  </div>
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wider">
                    总分
                  </div>
                </div>

                {/* 维度摘要 */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-muted-foreground">最强:</span>
                    <span className="text-green-600 font-medium">
                      {item.top_dim}
                    </span>
                    <span className="text-muted-foreground mx-1">·</span>
                    <span className="text-muted-foreground">待改进:</span>
                    <span className="text-red-500 font-medium">
                      {item.bottom_dim}
                    </span>
                  </div>
                  <div className="mt-1.5 flex items-center gap-3 text-xs text-muted-foreground">
                    <span>{formatDate(item.evaluated_at)}</span>
                    {item.has_feedback ? (
                      <Badge variant="success" className="text-[10px]">
                        <MessageSquare className="mr-1 h-2.5 w-2.5" />
                        AI 反馈
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-[10px]">
                        未生成反馈
                      </Badge>
                    )}
                  </div>
                </div>

                <ArrowRight className="h-5 w-5 text-muted-foreground flex-shrink-0" />
              </div>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-center">还没有评估记录</CardTitle>
      </CardHeader>
      <CardContent className="text-center pb-8">
        <Mic className="mx-auto h-12 w-12 text-muted-foreground/40" />
        <p className="mt-4 text-sm text-muted-foreground">
          完成一次录音评估后,这里会显示历史记录。
        </p>
        <Button asChild variant="piano" className="mt-4">
          <Link href="/app/record">开始第一次录音</Link>
        </Button>
      </CardContent>
    </Card>
  );
}

function getScoreColor(score: number): string {
  if (score >= 85) return 'text-green-600';
  if (score >= 70) return 'text-piano-500';
  if (score >= 55) return 'text-amber-500';
  return 'text-red-500';
}
