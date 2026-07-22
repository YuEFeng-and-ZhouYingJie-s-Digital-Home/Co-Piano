'use client';

import { useSeniorMode } from '@/lib/use-senior-mode';

/**
 * 银发模式应用器 — client 组件,挂载时给 <html> 加/移除 senior class
 * globals.css 中 .senior 规则自动应用(大字体+高对比+简化动画)
 */
export function SeniorModeApplier({ isSenior }: { isSenior: boolean }) {
  useSeniorMode(isSenior);
  return null;
}
