import { Navbar } from '@/components/marketing/navbar';
import { Hero } from '@/components/marketing/hero';
import { FiveDimensions } from '@/components/marketing/five-dimensions';
import { Stats } from '@/components/marketing/stats';
import { RctChart } from '@/components/marketing/rct-chart';
import { CtaSection } from '@/components/marketing/cta-section';
import { Footer } from '@/components/marketing/footer';

export default function HomePage() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <Stats />
        <FiveDimensions />
        <section id="rct" className="py-20 md:py-28">
          <div className="container">
            <div className="mx-auto max-w-2xl text-center">
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl">
                RCT 验证的硬数据
              </h2>
              <p className="mt-4 text-lg text-muted-foreground">
                8 周随机对照试验,60 名学生,前测/后测控制组设计。
                CoPiano v3.0 效应量 <span className="font-semibold text-piano-500">d=1.34</span>,
                显著优于 Bloom 1985 辅导黄金标准 0.75。
              </p>
            </div>
            <div className="mt-12">
              <RctChart />
            </div>
          </div>
        </section>
        <CtaSection />
      </main>
      <Footer />
    </>
  );
}
