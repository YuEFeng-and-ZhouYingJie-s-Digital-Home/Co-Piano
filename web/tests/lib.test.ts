import { describe, it, expect } from 'vitest';
import { cn, truncate, formatPrice } from '@/lib/utils';

describe('lib/utils', () => {
  it('cn merges Tailwind classes correctly', () => {
    expect(cn('px-2', 'py-2', 'px-4')).toBe('py-2 px-4');
    expect(cn('text-red-500', 'text-blue-500')).toBe('text-blue-500');
    expect(cn('p-2', false && 'p-4', 'p-6')).toBe('p-6');
  });

  it('truncate handles short and long strings', () => {
    expect(truncate('hi', 10)).toBe('hi');
    expect(truncate('hello world', 5)).toBe('hell…');
  });

  it('formatPrice converts cents to yuan', () => {
    expect(formatPrice(0)).toMatch(/0/);
    expect(formatPrice(2900)).toMatch(/29/);
    expect(formatPrice(99900)).toMatch(/999/);
  });
});
