/**
 * 静态断言 — 确保组件的 CVA variants 名称稳定(shadcn/ui 升级时如改名会报错)
 * 不需要 React 渲染,只需把 CVA 函数当普通函数调用,验证其输出包含关键 className
 *
 * @vitest-environment node
 */
import { describe, it, expect } from 'vitest';
import { buttonVariants } from '@/components/ui/button';
import { badgeVariants } from '@/components/ui/badge';

describe('shadcn/ui CVA variants', () => {
  it('button default variant has primary bg', () => {
    const cls = buttonVariants({ variant: 'default' });
    expect(cls).toContain('bg-primary');
    expect(cls).toContain('text-primary-foreground');
  });

  it('button piano variant has piano brand color', () => {
    const cls = buttonVariants({ variant: 'piano' });
    expect(cls).toContain('bg-piano-500');
  });

  it('button outline variant has border', () => {
    const cls = buttonVariants({ variant: 'outline' });
    expect(cls).toContain('border');
    expect(cls).toContain('border-input');
  });

  it('button size sm/lg/icon produce correct heights', () => {
    expect(buttonVariants({ size: 'sm' })).toContain('h-9');
    expect(buttonVariants({ size: 'lg' })).toContain('h-11');
    expect(buttonVariants({ size: 'icon' })).toContain('h-10 w-10');
  });

  it('badge default has primary bg', () => {
    expect(badgeVariants({ variant: 'default' })).toContain('bg-primary');
  });

  it('badge success has green token', () => {
    expect(badgeVariants({ variant: 'success' })).toContain('green');
  });

  it('badge piano has brand color', () => {
    expect(badgeVariants({ variant: 'piano' })).toContain('piano-500');
  });
});
