import { notFound } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Calendar, Mic } from 'lucide-react';
import { auth } from '@/auth';
import { api, ApiError } from '@/lib/api';
import { FeedbackGenerator } from '@/components/feedback/feedback-generator';
import { EvaluationResult } from '@/components/record/evaluation-result';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatDate } from '@/lib/utils';
import type { Evaluation } from '@/lib/evaluation-types';
import type { Feedback } from '@/lib/feedback-types';

interface PageProps {
  params: { eval_id: string };
}

export async function generateMetadata({ params }: PageProps) {
  return { title: `反馈 · ${params.eval_id.slice(0, 8)}` };
}

export default async function FeedbackDetailPage({ params }: PageProps) {
  const session = await auth();
  if (!session?.accessToken) return null;

  // 并行拉 evaluation + feedback
  const [evRes, fbRes] = await Promise.allSettled([
    api.get<Evaluation>(`/api/v1/evaluations/${params.eval_id}`),
    api
      .get<Feedback>(`/api/v1/feedback/${params.eval_id}`)
      .catch((e) => {
        if (e instanceof ApiError && e.status === 404) return null;
        throw e;
      }),
  ]);

  if (evRes.status === 'rejected') {
    notFound();
  }
  const evaluation = evRes.value;
  const feedback = fbRes.status === 'fulfilled' ? fbRes.value : null;

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <Button asChild variant="ghost" size="sm" className="-ml-2">
        <Link href="/app/feedback">
          <ArrowLeft className="mr-1 h-3 w-3" />
          返回反馈历史
        </Link>
      </Button>

      {/* 评估概况 */}
      <div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Calendar className="h-3.5 w-3.5" />
          {formatDate(evaluation.created_at)}
          <Badge variant="outline" className="ml-2 font-mono text-[10px]">
            {evaluation.id.slice(0, 8)}
          </Badge>
        </div>
        <h1 className="mt-1 text-2xl font-bold tracking-tight">
          评估详情
        </h1>
      </div>

      {/* 5 维分项 */}
      <EvaluationResult evaluation={evaluation} />

      {/* AI 反馈 */}
      <Card>
        <CardHeader>
          <CardTitle>AI 教练反馈</CardTitle>
        </CardHeader>
        <CardContent>
          <FeedbackGenerator
            evaluationId={evaluation.id}
            initialFeedback={feedback}
          />
        </CardContent>
      </Card>

      {/* 后续操作 */}
      <Card>
        <CardContent className="pt-6 flex flex-wrap gap-2">
          <Button asChild variant="piano">
            <Link href={`/app/record?evaluation=${evaluation.id}`}>
              <Mic className="mr-1.5 h-4 w-4" />
              再录一次
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/app/progress">查看进度曲线</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
