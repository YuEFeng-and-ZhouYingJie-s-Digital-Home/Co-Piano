import Link from 'next/link';
import { ArrowRight, BookOpen, Mic, TrendingUp, Eye, Sparkles } from 'lucide-react';
import { auth } from '@/auth';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export default async function AppHomePage() {
  const session = await auth();
  const userName = session?.user?.name ?? session?.user?.email?.split('@')[0] ?? '同学';

  return (
    <div className="space-y-8">
      {/* Greeting */}
      <div>
        <Badge variant="piano" className="mb-3 gap-1.5">
          <Sparkles className="h-3 w-3" />
          AI 教练已就绪
        </Badge>
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          嗨,{userName} 👋
        </h1>
        <p className="mt-2 text-muted-foreground">
          今天练 1 小时,坚持 7 天,你的钢琴将脱胎换骨。
        </p>
      </div>

      {/* 今日推荐 */}
      <Card className="border-piano-500/30 bg-gradient-to-br from-piano-50 to-background dark:from-piano-900/20">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle>今日课程</CardTitle>
              <CardDescription>Day 3 · 表现力训练 · 9 维评分</CardDescription>
            </div>
            <Badge>推荐</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-3">
            <Button asChild variant="piano">
              <Link href="/app/curriculum">
                开始学习
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/app/record">直接录音评估</Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 快捷功能 */}
      <div>
        <h2 className="text-lg font-semibold mb-4">快捷功能</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <QuickCard
            href="/app/curriculum"
            icon={BookOpen}
            title="7 天课程"
            desc="自适应规划 + SM-2 复习"
          />
          <QuickCard
            href="/app/record"
            icon={Mic}
            title="录音评估"
            desc="5 维 AI 实时打分"
          />
          <QuickCard
            href="/app/progress"
            icon={TrendingUp}
            title="成长曲线"
            desc="5 维 Recharts 可视化"
          />
          <QuickCard
            href="/app/sight-reading"
            icon={Eye}
            title="视奏训练"
            desc="4 难度 × 3 模式"
          />
        </div>
      </div>

      {/* 上次评估 */}
      <Card>
        <CardHeader>
          <CardTitle>上次评估</CardTitle>
          <CardDescription>等待你的第一次录音...</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            接入 MIDI 键盘或上传 MIDI 文件,5 维 AI 立刻给出反馈。
          </p>
          <Button asChild variant="outline" className="mt-3">
            <Link href="/app/record">
              开始第一次录音
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

function QuickCard({
  href,
  icon: Icon,
  title,
  desc,
}: {
  href: string;
  icon: typeof BookOpen;
  title: string;
  desc: string;
}) {
  return (
    <Link href={href}>
      <Card className="h-full transition-all hover:shadow-md hover:-translate-y-0.5 cursor-pointer">
        <CardContent className="pt-6">
          <Icon className="h-7 w-7 text-piano-500" />
          <h3 className="mt-3 font-semibold">{title}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{desc}</p>
        </CardContent>
      </Card>
    </Link>
  );
}
