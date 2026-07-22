import { notFound } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { auth } from '@/auth';
import { api, ApiError } from '@/lib/api';
import { QuestionRunner } from '@/components/sight-reading/question-runner';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import type { SightReadingSession } from '@/lib/sight-reading-types';

interface PageProps {
  params: { id: string };
}

export async function generateMetadata({ params }: PageProps) {
  return { title: `视奏训练 · ${params.id.slice(0, 8)}` };
}

export default async function SightReadingSessionPage({ params }: PageProps) {
  const session = await auth();
  if (!session?.accessToken) return null;

  let sr: SightReadingSession;
  try {
    sr = await api.get<SightReadingSession>(`/api/v1/sight-reading/${params.id}`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    return (
      <div className="space-y-4">
        <BackToList />
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            无法加载训练 session
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <BackToList />
      <QuestionRunner session={sr} />
    </div>
  );
}

function BackToList() {
  return (
    <Button asChild variant="ghost" size="sm" className="-ml-2">
      <Link href="/app/sight-reading">
        <ArrowLeft className="mr-1 h-3 w-3" />
        返回视奏训练
      </Link>
    </Button>
  );
}
