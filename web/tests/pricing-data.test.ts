import { describe, it, expect } from 'vitest';
import {
  PRICING_TIERS,
  PRICING_FAQS,
  formatCny,
  getTierById,
  type PricingTier,
} from '@/lib/pricing-data';

describe('pricing data', () => {
  it('has 5 tiers', () => {
    expect(PRICING_TIERS).toHaveLength(5);
  });

  it('tier ids are unique', () => {
    const ids = PRICING_TIERS.map((t) => t.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('all tiers have features', () => {
    PRICING_TIERS.forEach((t) => {
      expect(t.features.length).toBeGreaterThanOrEqual(3);
    });
  });

  it('Pro tier is highlighted', () => {
    const pro = getTierById('pro');
    expect(pro?.highlighted).toBe(true);
    expect(pro?.monthlyCents).toBe(2900);
  });

  it('Senior tier is free', () => {
    const senior = getTierById('senior');
    expect(senior?.monthlyCents).toBe(0);
    expect(senior?.yearlyCents).toBe(0);
  });

  it('yearly is cheaper than 12×monthly for paid tiers', () => {
    PRICING_TIERS.filter((t) => t.monthlyCents > 0).forEach((t) => {
      const twelveMonths = t.monthlyCents * 12;
      expect(t.yearlyCents).toBeLessThan(twelveMonths);
      // ~17% off
      const discount = 1 - t.yearlyCents / twelveMonths;
      expect(discount).toBeGreaterThan(0.15);
      expect(discount).toBeLessThan(0.2);
    });
  });

  it('formatCny renders free and paid correctly', () => {
    expect(formatCny(0)).toBe('免费');
    expect(formatCny(2900)).toBe('¥29/月');
    expect(formatCny(2900, 'yearly')).toBe('¥290/年');
  });

  it('getTierById returns undefined for unknown id', () => {
    expect(getTierById('unknown' as PricingTier['id'])).toBeUndefined();
  });

  it('FAQ has at least 5 items', () => {
    expect(PRICING_FAQS.length).toBeGreaterThanOrEqual(5);
  });
});
