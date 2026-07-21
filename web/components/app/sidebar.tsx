'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Music2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { NAV_ITEMS } from '@/lib/nav-items';

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden lg:flex lg:flex-col lg:w-64 lg:fixed lg:inset-y-0 lg:border-r lg:border-border lg:bg-card">
      {/* Logo */}
      <div className="flex h-16 items-center gap-2 border-b border-border px-6">
        <Link href="/app" className="flex items-center gap-2 font-bold text-lg">
          <Music2 className="h-6 w-6 text-piano-500" />
          <span>CoPiano</span>
        </Link>
      </div>

      {/* Nav items */}
      <nav className="flex-1 space-y-1 overflow-y-auto p-4">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive =
            item.href === '/app' ? pathname === '/app' : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'group flex items-start gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors',
                isActive
                  ? 'bg-piano-500/10 text-piano-700 dark:text-piano-300'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground',
              )}
            >
              <Icon
                className={cn(
                  'h-5 w-5 flex-shrink-0 mt-0.5',
                  isActive ? 'text-piano-500' : 'text-muted-foreground group-hover:text-foreground',
                )}
              />
              <div className="flex-1 min-w-0">
                <div className="font-medium">{item.label}</div>
                {item.description && (
                  <div className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                    {item.description}
                  </div>
                )}
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Footer / version */}
      <div className="border-t border-border p-4 text-xs text-muted-foreground">
        <div>CoPiano v4.0</div>
        <div className="mt-1">© 2026</div>
      </div>
    </aside>
  );
}
