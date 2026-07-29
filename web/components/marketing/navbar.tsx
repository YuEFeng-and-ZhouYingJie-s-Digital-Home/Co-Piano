import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { docsUrl } from '@/lib/urls';

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between">
        <Link href="/" className="flex items-center gap-2 font-bold text-lg">
          <span className="text-2xl">🎹</span>
          <span>CoPiano</span>
        </Link>
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-muted-foreground">
          <Link href="#five-dimensions" className="hover:text-foreground transition-colors">
            5 维评估
          </Link>
          <Link href="#rct" className="hover:text-foreground transition-colors">
            RCT 数据
          </Link>
          <Link href="/pricing" className="hover:text-foreground transition-colors">
            价格
          </Link>
          <Link href="/about" className="hover:text-foreground transition-colors">
            关于
          </Link>
          <Link
            href={docsUrl()}
            className="hover:text-foreground transition-colors"
          >
            文档
          </Link>
        </nav>
        <div className="flex items-center gap-2">
          <Button asChild variant="ghost" size="sm">
            <Link href="/login">登录</Link>
          </Button>
          <Button asChild variant="piano" size="sm">
            <Link href="/signup">免费开始</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
