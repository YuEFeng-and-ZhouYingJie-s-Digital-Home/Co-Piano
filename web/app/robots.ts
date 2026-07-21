import type { MetadataRoute } from 'next';

const BASE_URL = process.env.NEXT_PUBLIC_MARKETING_URL ?? 'https://copiano.com';

export default function robots(): MetadataRoute.Robots {
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
    sitemap: `${BASE_URL}/sitemap.xml`,
    host: BASE_URL,
  };
}
