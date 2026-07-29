import type { Metadata, Viewport } from 'next';
import { headers } from 'next/headers';
import { Inter, JetBrains_Mono } from 'next/font/google';
import { StructuredData } from '@/components/marketing/structured-data';
import { Providers } from '@/components/providers';
import { siteUrl, hostFromHeaders } from '@/lib/urls';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

/**
 * 运行时 metadata — 从 request headers 读 host,让 canonical/OG
 * 在 localhost / *.trycloudflare.com / yefzyj.top 都正确
 * 同一个 build,无需 rebuild
 */
export async function generateMetadata(): Promise<Metadata> {
  const { host, proto } = hostFromHeaders((k) => headers().get(k));
  const base = siteUrl(host, proto);

  return {
    metadataBase: new URL(base),
    title: {
      default: 'CoPiano — AI 古典钢琴教练',
      template: '%s | CoPiano',
    },
    description:
      '5 维 AI 评估 + 7 天自适应课程 + RCT 验证 (d=1.34)。从初学者到演奏家,让钢琴学习像打游戏一样有趣。',
    keywords: [
      'AI 钢琴',
      '钢琴教练',
      '古典钢琴',
      '钢琴学习',
      'MIDI',
      'AI 教育',
      '五维评估',
      '自适应课程',
      '视奏训练',
      '银发',
    ],
    authors: [{ name: 'CoPiano Team' }],
    creator: 'CoPiano',
    publisher: 'CoPiano',
    formatDetection: { email: false, address: false, telephone: false },
    alternates: {
      canonical: base,
      languages: {
        'zh-CN': base,
        en: `${base}/en`,
      },
    },
    openGraph: {
      type: 'website',
      locale: 'zh_CN',
      url: base,
      title: 'CoPiano — AI 古典钢琴教练',
      description: '5 维 AI 评估 + RCT 验证 (d=1.34)。让钢琴学习更聪明。',
      siteName: 'CoPiano',
      images: [
        {
          url: '/opengraph-image',
          width: 1200,
          height: 630,
          alt: 'CoPiano — AI 古典钢琴教练',
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title: 'CoPiano — AI 古典钢琴教练',
      description: '5 维 AI 评估 + RCT 验证 d=1.34。',
      images: ['/twitter-image'],
      creator: '@copiano',
    },
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        'max-image-preview': 'large',
        'max-snippet': -1,
      },
    },
    verification: {
      // 部署后填入真实 code
      google: process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION,
    },
  };
}

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: 'white' },
    { media: '(prefers-color-scheme: dark)', color: '#2c0b75' },
  ],
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen bg-background font-sans antialiased">
        <StructuredData />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
