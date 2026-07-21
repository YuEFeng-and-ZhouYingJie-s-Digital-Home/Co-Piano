import type { Metadata } from 'next';
import { Mail, MessageSquare, Github, FileText, Sparkles, TrendingUp } from 'lucide-react';
import { Navbar } from '@/components/marketing/navbar';
import { Footer } from '@/components/marketing/footer';
import { CtaSection } from '@/components/marketing/cta-section';
import { TeamCards } from '@/components/marketing/team-cards';
import { Timeline } from '@/components/marketing/timeline';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { TEAM, TIMELINE, PAPER, CONTACT } from '@/lib/about-data';

export const metadata: Metadata = {
  title: '关于 — CoPiano',
  description: 'CoPiano 团队、CoPiano v3 arXiv 论文、发展时间线。RCT 验证 d=1.34。',
  openGraph: {
    title: '关于 CoPiano — 团队与论文',
    description: '5 维 AI 钢琴教练, RCT 验证 d=1.34。',
  },
};

export default function AboutPage() {
  return (
    <>
      <Navbar />
      <main>
        {/* Hero */}
        <section className="border-b border-border/40 bg-gradient-to-b from-piano-50/50 to-background dark:from-piano-900/10 py-16 md:py-20">
          <div className="container text-center">
            <Badge variant="piano" className="mb-4 gap-1.5">
              <Sparkles className="h-3 w-3" />
              Our Mission
            </Badge>
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
              让每个人都能享受
              <br />
              <span className="bg-gradient-to-r from-piano-500 to-piano-300 bg-clip-text text-transparent">
                钢琴学习的乐趣
              </span>
            </h1>
            <p className="mt-6 text-lg text-muted-foreground max-w-2xl mx-auto">
              CoPiano 由音乐 + AI 交叉团队创建。
              我们相信 AI 不是要取代老师,而是让每个认真学琴的人,
              都能以低成本获得专业级的反馈。
            </p>
          </div>
        </section>

        {/* Team */}
        <section className="py-16 md:py-20">
          <div className="container">
            <div className="mx-auto max-w-2xl text-center mb-12">
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">团队</h2>
              <p className="mt-3 text-muted-foreground">
                音乐家 × AI 工程师 × 教育学家的跨界组合
              </p>
            </div>
            <TeamCards members={TEAM} />
          </div>
        </section>

        {/* Paper */}
        <section id="paper" className="border-y border-border/40 bg-muted/30 py-16 md:py-20">
          <div className="container">
            <div className="mx-auto max-w-4xl">
              <div className="text-center mb-12">
                <Badge variant="piano" className="mb-4 gap-1.5">
                  <FileText className="h-3 w-3" />
                  论文
                </Badge>
                <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
                  CoPiano v3
                </h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  arXiv 草稿 · 2026
                </p>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg leading-relaxed">
                    {PAPER.title}
                  </CardTitle>
                  <CardDescription>
                    {PAPER.authors} · {PAPER.year} · {PAPER.venue}
                  </CardDescription>
                  <Badge variant="outline" className="w-fit mt-2">
                    {PAPER.status}
                  </Badge>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div>
                    <h3 className="text-sm font-semibold text-muted-foreground mb-2">摘要</h3>
                    <p className="text-sm leading-relaxed text-foreground/90">
                      {PAPER.abstract}
                    </p>
                  </div>

                  <div>
                    <h3 className="text-sm font-semibold text-muted-foreground mb-3">关键结果</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {PAPER.results.map((r) => (
                        <div key={r.metric} className="rounded-lg border border-border bg-background p-3 text-center">
                          <div className="text-xs text-muted-foreground">{r.metric}</div>
                          <div className="mt-1 text-2xl font-bold text-piano-500">
                            {r.value}
                          </div>
                          <div className="mt-1 text-[10px] text-muted-foreground leading-tight">
                            {r.label}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-semibold text-muted-foreground mb-2">代码/数据</h3>
                    <div className="flex flex-wrap gap-2 text-xs">
                      <Badge variant="secondary">{PAPER.code.scripts} 脚本</Badge>
                      <Badge variant="secondary">{PAPER.code.loc} LOC</Badge>
                      <Badge variant="secondary">{PAPER.code.tests} 测试</Badge>
                      <Badge variant="secondary">{PAPER.code.paperFigures} 图表</Badge>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-3 pt-2">
                    <Button asChild variant="piano">
                      <a href="/docs/paper-v3.pdf">
                        <FileText className="mr-2 h-4 w-4" />
                        下载 PDF (待发布)
                      </a>
                    </Button>
                    <Button asChild variant="outline">
                      <a href={CONTACT.github}>
                        <Github className="mr-2 h-4 w-4" />
                        GitHub
                      </a>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </section>

        {/* Timeline */}
        <section className="py-16 md:py-20">
          <div className="container">
            <div className="mx-auto max-w-2xl text-center mb-12">
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">发展时间线</h2>
              <p className="mt-3 text-muted-foreground">
                从 v1.0 AMT 基线到 v4.0 全栈产品
              </p>
            </div>
            <div className="mx-auto max-w-2xl">
              <Timeline items={TIMELINE} />
            </div>
          </div>
        </section>

        {/* Contact */}
        <section className="border-t border-border/40 bg-muted/30 py-16 md:py-20">
          <div className="container">
            <div className="mx-auto max-w-2xl text-center">
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">联系我们</h2>
              <p className="mt-3 text-muted-foreground">
                合作 / 投稿 / 媒体采访 / 用户支持
              </p>
            </div>
            <div className="mt-12 mx-auto max-w-3xl grid gap-4 md:grid-cols-2">
              <Card>
                <CardContent className="pt-6">
                  <Mail className="h-6 w-6 text-piano-500" />
                  <h3 className="mt-3 font-semibold">一般咨询</h3>
                  <a
                    href={`mailto:${CONTACT.email}`}
                    className="mt-1 block text-sm text-piano-500 underline"
                  >
                    {CONTACT.email}
                  </a>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <FileText className="h-6 w-6 text-piano-500" />
                  <h3 className="mt-3 font-semibold">媒体采访</h3>
                  <a
                    href={`mailto:${CONTACT.press}`}
                    className="mt-1 block text-sm text-piano-500 underline"
                  >
                    {CONTACT.press}
                  </a>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <MessageSquare className="h-6 w-6 text-piano-500" />
                  <h3 className="mt-3 font-semibold">微信公众号</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    搜索: <code className="rounded bg-muted px-1">{CONTACT.wechat}</code>
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <Github className="h-6 w-6 text-piano-500" />
                  <h3 className="mt-3 font-semibold">开源仓库</h3>
                  <a
                    href={CONTACT.github}
                    className="mt-1 block text-sm text-piano-500 underline break-all"
                  >
                    {CONTACT.github}
                  </a>
                </CardContent>
              </Card>
            </div>
          </div>
        </section>

        <CtaSection />
      </main>
      <Footer />
    </>
  );
}
