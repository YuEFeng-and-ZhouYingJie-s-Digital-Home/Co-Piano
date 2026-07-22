import { auth } from '@/auth';
import { api, ApiError } from '@/lib/api';
import { ProgressDashboard } from '@/components/progress/progress-dashboard';
import { evaluationsToPoints } from '@/lib/progress-types';
import { Card, CardContent } from '@/components/ui/card';
import type { Evaluation } from '@/lib/evaluation-types';

export const metadata = { title: '进度曲线' };

export default async function ProgressPage() {
  const session = await auth();
  if (!session?.accessToken) return null;

  let evaluations: Evaluation[] = [];
  let error: string | null = null;

  try {
    evaluations = await api.get<Evaluation[]>('/api/v1/evaluations');
  } catch (e) {
    error = e instanceof ApiError ? e.detail : '无法加载评估历史';
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-sm text-muted-foreground">
          {error}
        </CardContent>
      </Card>
    );
  }

  const allPoints = evaluationsToPoints(evaluations);

  return <ProgressDashboard allPoints={allPoints} />;
}
