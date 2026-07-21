'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';
import { NAV_ITEMS } from '@/lib/nav-items';

/**
 * 移动端导航 — 底部 5 tab + 抽屉式完整菜单
 */
export function MobileNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const primaryItems = NAV_ITEMS.filter((i) => i.primary);

  return (
    <>
      {/* 顶部条 — logo + 菜单按钮 */}
      <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-border bg-background/95 px-4 backdrop-blur lg:hidden">
        <Link href="/app" className="flex items-center gap-2 font-bold">
          <span className="text-xl">🎹</span>
          <span>CoPiano</span>
        </Link>
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="rounded-md p-2 hover:bg-muted"
          aria-label="打开菜单"
        >
          <Menu className="h-5 w-5" />
        </button>
      </header>

      {/* 抽屉 */}
      {open && (
        <>
          <div
            className="fixed inset-0 z-50 bg-black/50 lg:hidden"
            onClick={() => setOpen(false)}
            aria-hidden
          />
          <nav className="fixed inset-y-0 right-0 z-50 w-72 max-w-[80vw] border-l border-border bg-card p-4 lg:hidden">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold">菜单</h2>
              <button
                onClick={() => setOpen(false)}
                className="rounded-md p-1 text-muted-foreground hover:bg-muted"
                aria-label="关闭"
              >
                ✕
              </button>
            </div>
            <div className="space-y-1">
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                const isActive =
                  item.href === '/app' ? pathname === '/app' : pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setOpen(false)}
                    className={cn(
                      'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm',
                      isActive
                        ? 'bg-piano-500/10 text-piano-700'
                        : 'text-muted-foreground hover:bg-muted',
                    )}
                  >
                    <Icon className="h-5 w-5" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </nav>
        </>
      )}

      {/* 底部 tab bar — 5 个 primary */}
      <nav className="fixed bottom-0 left-0 right-0 z-40 border-t border-border bg-background/95 backdrop-blur lg:hidden">
        <div className="grid grid-cols-5">
          {primaryItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.href === '/app' ? pathname === '/app' : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex flex-col items-center justify-center gap-1 py-2 text-xs',
                  isActive ? 'text-piano-500' : 'text-muted-foreground',
                )}
              >
                <Icon className="h-5 w-5" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
