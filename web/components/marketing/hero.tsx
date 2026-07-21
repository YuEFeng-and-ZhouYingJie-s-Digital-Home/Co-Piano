import Link from 'next/link';
import { ArrowRight, Sparkles, Music } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-border/40">
      {/* gradient background */}
      <div className="absolute inset-0 -z-10 bg-gradient-to-br from-piano-50 via-background to-background dark:from-piano-900/20" />
      <div
        className="absolute inset-x-0 top-0 -z-10 h-[600px] bg-[radial-gradient(ellipse_at_top,rgba(107,44,255,0.15),transparent_60%)]"
        aria-hidden
      />

      <div className="container py-20 md:py-32">
        <div className="mx-auto max-w-3xl text-center">
          <Badge variant="piano" className="mb-6 gap-1.5">
            <Sparkles className="h-3 w-3" />
            RCT 验证: 效应量 d=1.34(超 Bloom 1985 0.75 的 1.8 倍)
          </Badge>

          <h1 className="text-4xl font-bold tracking-tight sm:text-6xl md:text-7xl">
            让钢琴学习
            <br />
            <span className="bg-gradient-to-r from-piano-500 to-piano-300 bg-clip-text text-transparent">
              像打游戏一样有趣
            </span>
          </h1>

          <p className="mt-6 text-lg leading-8 text-muted-foreground sm:text-xl">
            CoPiano 用 <strong className="text-foreground">5 维 AI 评估</strong> +
            {' '}<strong className="text-foreground">7 天自适应课程</strong> +
            {' '}<strong className="text-foreground">LLM 个性化反馈</strong>,
            从初学者到演奏家,每一个音符都被认真听见。
          </p>

          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Button asChild variant="piano" size="lg" className="min-w-[180px]">
              <Link href="https://app.copiano.com/signup">
                免费开始 7 天
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg" className="min-w-[180px]">
              <Link href="#rct">
                <Music className="mr-2 h-4 w-4" />
                看 RCT 数据
              </Link>
            </Button>
          </div>

          <p className="mt-6 text-sm text-muted-foreground">
            无需信用卡 · Web MIDI 即插即用 · 5 分钟上手
          </p>
        </div>
      </div>
    </section>
  );
}
