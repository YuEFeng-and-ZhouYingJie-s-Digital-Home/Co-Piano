import type { MetadataRoute } from 'next';
import { headers } from 'next/headers';
import { siteUrl, hostFromHeaders } from '@/lib/urls';

// 强制动态 — robots.txt 里的 sitemap/host 跟当前 host 走
export const dynamic = 'force-dynamic';

export default function robots(): MetadataRoute.Robots {
  const { host, proto } = hostFromHeaders((k) => headers().get(k));
  const base = siteUrl(host, proto);

  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/api/', '/app/'],
      },
      {
        // Google 爬虫 - 允许全部
        userAgent: 'Googlebot',
        allow: '/',
        disallow: ['/api/'],
      },
    ],
    sitemap: `${base}/sitemap.xml`,
    host: base,
  };
}
