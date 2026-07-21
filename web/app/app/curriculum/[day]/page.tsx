import { notFound } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Calendar, Clock, Target } from 'lucide-react';
import { auth } from '@/auth';
import { api, ApiError } from '@/lib/api';
import { BlockCard } from '@/components/curriculum/block-card';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { DIMENSION_META, type CurriculumDay, type DimensionName } from '@/lib/curriculum-types';

interface PageProps {
  params: { day: string };
}

export async function generateMetadata({ params }: PageProps) {
  return { title: `Day ${params.day} · 课程` };
}

export default async function DayDetailPage({ params }: PageProps) {
  const dayNum = Number(params.day);
  if (!Number.isInteger(dayNum) || dayNum < 1 || dayNum > 7) {
    notFound();
  }

  const session = await auth();
  if (!session?.accessToken) return null;

  let day: CurriculumDay | null = null;
  let error: string | null = null;
  try {
    day = await api.get<CurriculumDay>(`/api/v1/curriculum/${dayNum}`);
  } catch (e) {
    if (e instanceof ApiError) {
      error = e.detail;
    } else {
      error = '无法加载';
    }
  }

  if (error || !day) {
    return (
      <div className="space-y-4">
        <BackButton />
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">{error ?? '课程加载失败'}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const doneCount = day.blocks.filter((b) => b.completed).length;
  const progressPct = (doneCount / day.blocks.length) * 100;
  const focusMeta = day.focus_dimension
    ? DIMENSION_META[day.focus_dimension as DimensionName]
    : null;

  return (
    <div className="space-y-6">
      <BackButton />

      {/* Day header */}
      <div>
        <div className="flex items-center gap-3 mb-2 flex-wrap">
          <Badge variant="piano">Day {day.day_num}</Badge>
          {day.completed && <Badge variant="success">已完成</Badge>}
          {focusMeta && (
            <Badge variant="outline" className="gap-1">
              {focusMeta.emoji} 重点: {focusMeta.label}
            </Badge>
          )}
        </div>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
          {day.title}
        </h1>
        <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5" />
            {new Date(day.date).toLocaleDateString('zh-CN', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
              weekday: 'long',
            })}
          </div>
          <div className="flex items-center gap-1">
            <Clock className="h-3.5 w-3.5" />
            {day.total_min} 分钟
          </div>
          <div className="flex items-center gap-1">
            <Target className="h-3.5 w-3.5" />
            {doneCount}/{day.blocks.length} 块完成
          </div>
        </div>
        {/* 进度条 */}
        <div className="mt-3 h-2 rounded-full bg-muted overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-piano-500 to-green-500 transition-all"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Block 列表 */}
      <div className="space-y-3">
        {day.blocks
          .sort((a, b) => a.order - b.order)
          .map((block) => (
            <BlockCard key={block.id} block={block} />
          ))}
      </div>

      {day.completed && (
        <Card className="border-green-500/30 bg-green-500/5">
          <CardContent className="pt-6 text-center">
            <p className="font-semibold text-green-700 dark:text-green-300">
              🎉 Day {day.day_num} 全部完成!
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              继续坚持,明天还有新课程等你。
            </p>
            <Button asChild variant="outline" className="mt-3">
              <Link href="/app/curriculum">返回课程总览</Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function BackButton() {
  return (
    <Button asChild variant="ghost" size="sm" className="-ml-2">
      <Link href="/app/curriculum">
        <ArrowLeft className="mr-1 h-3 w-3" />
        返回 7 天课程
      </Link>
    </Button>
  );
}
