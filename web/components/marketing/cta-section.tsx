import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function CtaSection() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-piano-500 to-piano-700 py-20 text-white md:py-28">
      <div
        className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(255,255,255,0.1),transparent_70%)]"
        aria-hidden
      />
      <div className="container relative">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl">
            准备好开始了吗?
          </h2>
          <p className="mt-4 text-lg text-piano-100">
            5 分钟接入 MIDI 键盘,马上体验 5 维 AI 评估。
            银发模式免费。
          </p>
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Button
              asChild
              size="lg"
              className="min-w-[200px] bg-white text-piano-700 hover:bg-piano-50"
            >
              <Link href="/signup">
                免费开始
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="min-w-[200px] border-white/30 bg-white/10 text-white hover:bg-white/20"
            >
              <Link href="/pricing">查看价格</Link>
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
