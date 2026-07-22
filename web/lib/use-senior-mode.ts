'use client';

import { useEffect } from 'react';

/**
 * 客户端 hook:在 <html> 根元素上添加/移除 'senior' class
 * 用法:在 client 组件挂载时调用 useSeniorMode(isSenior)
 */
export function useSeniorMode(isSenior: boolean) {
  useEffect(() => {
    if (typeof document === 'undefined') return;
    const root = document.documentElement;
    if (isSenior) {
      root.classList.add('senior');
      root.setAttribute('data-mode', 'senior');
    } else {
      root.classList.remove('senior');
      root.removeAttribute('data-mode');
    }
    return () => {
      root.classList.remove('senior');
      root.removeAttribute('data-mode');
    };
  }, [isSenior]);
}
