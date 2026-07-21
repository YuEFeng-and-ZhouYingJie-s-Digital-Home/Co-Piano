'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { formatCny, type BillingCycle, type PricingTier } from '@/lib/pricing-data';

interface PricingCardsProps {
  tiers: PricingTier[];
}

export function PricingCards({ tiers }: PricingCardsProps) {
  const [cycle, setCycle] = useState<BillingCycle>('monthly');

  return (
    <div>
      {/* 月付/年付切换 */}
      <div className="mb-8 flex items-center justify-center gap-1 rounded-full border border-border bg-muted/50 p-1 w-fit mx-auto">
        <button
          type="button"
          onClick={() => setCycle('monthly')}
          className={cn(
            'rounded-full px-4 py-1.5 text-sm font-medium transition-colors',
            cycle === 'monthly'
              ? 'bg-background text-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground',
          )}
        >
          月付
        </button>
        <button
          type="button"
          onClick={() => setCycle('yearly')}
          className={cn(
            'rounded-full px-4 py-1.5 text-sm font-medium transition-colors flex items-center gap-1.5',
            cycle === 'yearly'
              ? 'bg-background text-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground',
          )}
        >
          年付
          <Badge variant="success" className="ml-1 text-[10px] py-0">省 17%</Badge>
        </button>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {tiers.map((tier) => {
          const price = cycle === 'monthly' ? tier.monthlyCents : tier.yearlyCents;
          const isHighlighted = tier.highlighted;
          return (
            <Card
              key={tier.id}
              className={cn(
                'relative flex flex-col transition-all',
                isHighlighted
                  ? 'border-piano-500 shadow-xl scale-105 z-10'
                  : 'hover:shadow-md',
              )}
            >
              {tier.badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <Badge
                    variant={tier.id === 'senior' ? 'success' : 'piano'}
                    className="px-3"
                  >
                    {tier.badge}
                  </Badge>
                </div>
              )}

              <CardHeader>
                <CardTitle className="text-xl">{tier.name}</CardTitle>
                <CardDescription className="min-h-[2.5rem]">
                  {tier.tagline}
                </CardDescription>
                <div className="mt-4">
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-bold tracking-tight">
                      {tier.monthlyCents === 0 ? '¥0' : `¥${(price / 100).toFixed(0)}`}
                    </span>
                    {tier.monthlyCents > 0 && (
                      <span className="text-sm text-muted-foreground">
                        /{cycle === 'monthly' ? '月' : '年'}
                      </span>
                    )}
                  </div>
                  {cycle === 'yearly' && tier.monthlyCents > 0 && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      约 ¥{(price / 12 / 100).toFixed(0)}/月 ·{' '}
                      <span className="text-green-600 dark:text-green-400 font-medium">
                        省 ¥{((tier.monthlyCents * 12 - price) / 100).toFixed(0)}
                      </span>
                    </p>
                  )}
                  {tier.monthlyCents === 0 && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      永久免费
                    </p>
                  )}
                </div>
              </CardHeader>

              <CardContent className="flex-1">
                <ul className="space-y-2.5">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2 text-sm">
                      <Check
                        className={cn(
                          'h-4 w-4 flex-shrink-0 mt-0.5',
                          isHighlighted ? 'text-piano-500' : 'text-muted-foreground',
                        )}
                      />
                      <span className="text-foreground/90">{feature}</span>
                    </li>
                  ))}
                </ul>
                {tier.limits && (
                  <div className="mt-4 rounded-md bg-muted/50 p-3 text-xs space-y-1">
                    {tier.limits.map((limit) => (
                      <div key={limit.label} className="flex justify-between">
                        <span className="text-muted-foreground">{limit.label}</span>
                        <span className="font-medium">{limit.value}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>

              <CardFooter>
                <Button
                  asChild
                  variant={isHighlighted ? 'piano' : 'outline'}
                  className="w-full"
                >
                  <Link href={tier.ctaHref}>{tier.cta}</Link>
                </Button>
              </CardFooter>
            </Card>
          );
        })}
      </div>

      <p className="mt-6 text-center text-xs text-muted-foreground">
        所有价格含税 · 支付宝/微信/Stripe 信用卡 · 学校方案可开具增值税专票
      </p>
    </div>
  );
}
