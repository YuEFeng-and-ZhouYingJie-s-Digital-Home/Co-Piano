import Link from 'next/link';
import { Separator } from '@/components/ui/separator';

const FOOTER_LINKS = {
  产品: [
    { label: '5 维评估', href: '#five-dimensions' },
    { label: '课程系统', href: 'https://app.copiano.com/curriculum' },
    { label: '视奏训练', href: 'https://app.copiano.com/sight-reading' },
    { label: '银发模式', href: '#senior' },
  ],
  资源: [
    { label: '价格', href: '/pricing' },
    { label: '论文 (arXiv)', href: '/about#paper' },
    { label: '文档', href: 'https://docs.copiano.com' },
    { label: 'API', href: 'https://docs.copiano.com/api' },
  ],
  公司: [
    { label: '关于团队', href: '/about' },
    { label: '联系我们', href: 'mailto:hi@copiano.com' },
    { label: '隐私政策', href: '/privacy' },
    { label: '服务条款', href: '/terms' },
  ],
} as const;

export function Footer() {
  return (
    <footer className="border-t border-border/40 bg-muted/20 py-12 md:py-16">
      <div className="container">
        <div className="grid gap-8 md:grid-cols-4">
          <div>
            <Link href="/" className="flex items-center gap-2 text-lg font-bold">
              <span className="text-2xl">🎹</span>
              <span>CoPiano</span>
            </Link>
            <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
              AI 古典钢琴教练。让每个人都能享受钢琴学习的乐趣。
            </p>
            <p className="mt-4 text-xs text-muted-foreground">
              © 2026 CoPiano. All rights reserved.
            </p>
          </div>

          {Object.entries(FOOTER_LINKS).map(([category, links]) => (
            <div key={category}>
              <h3 className="text-sm font-semibold">{category}</h3>
              <ul className="mt-3 space-y-2">
                {links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <Separator className="my-8" />

        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
          <p>
            Made with 🎹 + ❤️ in 北京 · CoPiano v4.0
          </p>
          <p className="text-xs">
            本网站使用 Cloudflare 加速 · 服务器在
            <Link href="https://console.cloud.tencent.com" className="underline">
              腾讯云
            </Link>
          </p>
        </div>
      </div>
    </footer>
  );
}
