import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'CoPiano — AI 古典钢琴教练',
    short_name: 'CoPiano',
    description: '5 维 AI 评估 + 7 天自适应课程 + RCT 验证 d=1.34',
    start_url: '/',
    display: 'standalone',
    background_color: '#ffffff',
    theme_color: '#6b2cff',
    icons: [
      {
        src: '/icon-192.png',
        sizes: '192x192',
        type: 'image/png',
        purpose: 'any',
      },
      {
        src: '/icon-512.png',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'any',
      },
      {
        src: '/icon-512-maskable.png',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'maskable',
      },
    ],
    lang: 'zh-CN',
  };
}
