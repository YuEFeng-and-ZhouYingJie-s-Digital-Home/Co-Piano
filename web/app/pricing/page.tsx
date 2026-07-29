import type { Metadata } from 'next';
import { Navbar } from '@/components/marketing/navbar';
import { Footer } from '@/components/marketing/footer';
import { PricingCards } from '@/components/marketing/pricing-cards';
import { PricingFaq } from '@/components/marketing/pricing-faq';
import { CtaSection } from '@/components/marketing/cta-section';
import { PRICING_TIERS, PRICING_FAQS } from '@/lib/pricing-data';
import { contactMailto } from '@/lib/urls';

export const metadata: Metadata = {
  title: '价格 — CoPiano',
  description: '5 维 AI 钢琴教练订阅方案。Free / Pro ¥29 / Senior 免费 / Teacher ¥99 / School ¥999。',
  openGraph: {
    title: 'CoPiano 价格 — 5 维 AI 钢琴教练',
    description: 'Free 试用 7 天。银发长者永久免费。',
  },
};

export default function PricingPage() {
  return (
    <>
      <Navbar />
      <main>
        <section className="border-b border-border/40 bg-gradient-to-b from-piano-50/50 to-background dark:from-piano-900/10 py-16 md:py-20">
          <div className="container text-center">
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
              简单透明的价格
            </h1>
            <p className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto">
              从免费开始,认真学琴就升级 Pro。
              银发长者永久免费,这是我们对社会的承诺。
            </p>
          </div>
        </section>

        <section className="py-16 md:py-20">
          <div className="container">
            <PricingCards tiers={[...PRICING_TIERS]} />
          </div>
        </section>

        <section className="border-t border-border/40 bg-muted/30 py-16 md:py-20">
          <div className="container">
            <div className="mx-auto max-w-2xl text-center mb-12">
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
                常见问题
              </h2>
              <p className="mt-3 text-muted-foreground">
                没找到答案?
                {' '}
                <a href={contactMailto()} className="text-piano-500 underline">
                  发邮件给我们
                </a>
              </p>
            </div>
            <PricingFaq items={PRICING_FAQS} />
          </div>
        </section>

        <CtaSection />
      </main>
      <Footer />
    </>
  );
}
