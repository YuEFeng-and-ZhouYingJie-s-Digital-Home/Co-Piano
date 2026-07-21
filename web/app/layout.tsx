import type { Metadata, Viewport } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
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

export const metadata: Metadata = {
  metadataBase: new URL('https://copiano.com'),
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
  ],
  authors: [{ name: 'CoPiano Team' }],
  creator: 'CoPiano',
  openGraph: {
    type: 'website',
    locale: 'zh_CN',
    url: 'https://copiano.com',
    title: 'CoPiano — AI 古典钢琴教练',
    description: '5 维 AI 评估 + RCT 验证。让钢琴学习更聪明。',
    siteName: 'CoPiano',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'CoPiano — AI 古典钢琴教练',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'CoPiano — AI 古典钢琴教练',
    description: '5 维 AI 评估 + RCT 验证。',
    images: ['/og-image.png'],
  },
  robots: {
    index: true,
    follow: true,
  },
};

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
        {children}
      </body>
    </html>
  );
}
