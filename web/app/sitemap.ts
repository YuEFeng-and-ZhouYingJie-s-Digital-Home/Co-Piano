import type { MetadataRoute } from 'next';
import { headers } from 'next/headers';
import { siteUrl, hostFromHeaders } from '@/lib/urls';

// 强制动态 — sitemap 包含当前 host,每次请求生成
export const dynamic = 'force-dynamic';

export default function sitemap(): MetadataRoute.Sitemap {
  const { host, proto } = hostFromHeaders((k) => headers().get(k));
  const base = siteUrl(host, proto);
  const now = new Date();

  return [
    {
      url: `${base}/`,
      lastModified: now,
      changeFrequency: 'weekly',
      priority: 1.0,
      alternates: {
        languages: {
          'zh-CN': `${base}/`,
          en: `${base}/`,
        },
      },
    },
    {
      url: `${base}/pricing`,
      lastModified: now,
      changeFrequency: 'weekly',
      priority: 0.9,
    },
    {
      url: `${base}/about`,
      lastModified: now,
      changeFrequency: 'monthly',
      priority: 0.7,
    },
  ];
}
