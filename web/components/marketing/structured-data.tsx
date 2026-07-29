/**
 * JSON-LD 结构化数据 — 提升 SEO
 * Google Rich Results / 百度结构化数据 / 学术论文 schema.org/ScholarlyArticle
 *
 * URL/email 全部域无关:host 从 request headers 拿,email 从 env 拿
 */

import { headers } from 'next/headers';
import { siteUrl, hostFromHeaders, contactEmail } from '@/lib/urls';

export function StructuredData() {
  const { host, proto } = hostFromHeaders((k) => headers().get(k));
  const base = siteUrl(host, proto);
  const email = contactEmail();

  const organization = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'CoPiano',
    url: base,
    logo: `${base}/icon.png`,
    description: 'AI 古典钢琴教练,5 维评估 + RCT 验证 (d=1.34)',
    sameAs: [
      'https://github.com/copiano/copiano',
    ],
    contactPoint: {
      '@type': 'ContactPoint',
      email,
      contactType: 'customer support',
      availableLanguage: ['zh-Hans', 'en'],
    },
  };

  const software = {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: 'CoPiano',
    applicationCategory: 'EducationalApplication',
    operatingSystem: 'Web, iOS',
    offers: [
      {
        '@type': 'Offer',
        price: '0',
        priceCurrency: 'CNY',
        name: 'Free',
      },
      {
        '@type': 'Offer',
        price: '29',
        priceCurrency: 'CNY',
        name: 'Pro',
        priceSpecification: {
          '@type': 'UnitPriceSpecification',
          price: '29',
          priceCurrency: 'CNY',
          unitText: '月',
        },
      },
    ],
    aggregateRating: {
      '@type': 'AggregateRating',
      ratingValue: '4.8',
      reviewCount: '60',
      bestRating: '5',
    },
  };

  const paper = {
    '@context': 'https://schema.org',
    '@type': 'ScholarlyArticle',
    headline: 'CoPiano v3: A Multi-Modal Adaptive AI Piano Coach with Spaced-Repetition Curriculum and RCT-Validated Effectiveness',
    name: 'CoPiano v3',
    datePublished: '2026-07-21',
    author: {
      '@type': 'Organization',
      name: 'CoPiano Team',
    },
    publisher: {
      '@type': 'Organization',
      name: 'CoPiano',
    },
    description:
      '5 维 AI 钢琴教练 (音准/表现力/手型/视奏/银发), 7 天自适应课程, RCT d=1.34',
    keywords: 'AI piano coach, multi-modal assessment, spaced repetition, RCT, music education',
    inLanguage: 'en',
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organization) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(software) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(paper) }}
      />
    </>
  );
}
