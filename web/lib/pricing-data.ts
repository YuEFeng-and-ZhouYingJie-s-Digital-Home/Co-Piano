/**
 * CoPiano 订阅档位数据 — 单一来源,UI 与 API 都从这里读
 * 价格单位:分(避免浮点数)
 */

export type BillingCycle = 'monthly' | 'yearly';

export interface PricingTier {
  id: 'free' | 'pro' | 'senior' | 'teacher' | 'school';
  name: string;
  tagline: string;
  /** 月费 (分) — 年付时按 10 个月算,等于 16.7% off */
  monthlyCents: number;
  /** 年费 (分) — 已经折算过 */
  yearlyCents: number;
  /** 主要 CTA 标签 */
  cta: string;
  ctaHref: string;
  highlighted?: boolean;
  badge?: string;
  features: string[];
  /** 限制条件(为 free 档写) */
  limits?: { label: string; value: string }[];
}

export const PRICING_TIERS: PricingTier[] = [
  {
    id: 'free',
    name: 'Free',
    tagline: '试一下,看看 AI 评估是不是真的准。',
    monthlyCents: 0,
    yearlyCents: 0,
    cta: '免费开始',
    ctaHref: 'https://app.copiano.com/signup',
    features: [
      '5 维 AI 评估(全部维度)',
      '每天 3 次录音评估',
      '基础课程库(前 7 天)',
      '1 设备登录',
    ],
    limits: [
      { label: '录音次数', value: '3 次/天' },
      { label: '课程天数', value: '7 天' },
    ],
  },
  {
    id: 'pro',
    name: 'Pro',
    tagline: '认真学琴的人。每天练 1 小时,30 天见效。',
    monthlyCents: 2900, // ¥29
    yearlyCents: 29000, // ¥290/年 (≈ ¥24/月)
    cta: '升级 Pro',
    ctaHref: 'https://app.copiano.com/signup?plan=pro',
    highlighted: true,
    badge: '最受欢迎',
    features: [
      'Free 全部功能',
      '无限录音评估',
      '完整 90 天课程库',
      'LLM 个性化反馈(流式)',
      '进度曲线 + 历史回看',
      '3 设备登录',
    ],
  },
  {
    id: 'senior',
    name: 'Senior (银发)',
    tagline: '60+ 岁长者免费。简化 UI,大字体,慢节奏。',
    monthlyCents: 0,
    yearlyCents: 0,
    cta: '免费申请',
    ctaHref: 'https://app.copiano.com/signup?plan=senior',
    features: [
      'Pro 全部功能',
      '简化 UI(大字体 + 高对比)',
      '慢节奏教学法',
      '无广告',
      '专属客服',
      '60+ 岁长者完全免费',
    ],
    badge: '公益免费',
  },
  {
    id: 'teacher',
    name: 'Teacher',
    tagline: '钢琴老师。一个账号管全班 30 学生。',
    monthlyCents: 9900, // ¥99
    yearlyCents: 99000, // ¥990/年
    cta: '升级 Teacher',
    ctaHref: 'https://app.copiano.com/signup?plan=teacher',
    features: [
      'Pro 全部功能',
      '管理 30 个学生账号',
      '班级进度仪表盘',
      '统一布置课程',
      '学生评估报告导出 (PDF)',
      'API 接入 (Web MIDI)',
    ],
  },
  {
    id: 'school',
    name: 'School',
    tagline: '琴行/学校。定制化部署 + 技术对接。',
    monthlyCents: 99900, // ¥999
    yearlyCents: 999000, // ¥9,990/年
    cta: '联系销售',
    ctaHref: 'mailto:hi@copiano.com?subject=School%20Plan',
    features: [
      'Teacher 全部功能',
      '不限学生数',
      '私有部署(可选)',
      '定制 logo/品牌',
      'SLA 99.9% 保障',
      '专属技术对接',
      '培训 1 次',
    ],
  },
];

export const PRICING_FAQS = [
  {
    q: '我可以在订阅前试用 Pro 吗?',
    a: '可以。注册后自动获得 7 天 Pro 试用,无需信用卡。试用结束后自动降级为 Free,你可以随时升级。',
  },
  {
    q: '可以随时取消订阅吗?',
    a: '可以。账户 → 设置 → 订阅,一键取消。已支付周期内继续享受 Pro 权限,周期结束后不扣费。',
  },
  {
    q: '60+ 岁长者如何申请免费?',
    a: '注册时选择"银发模式",我们不验证年龄,但请尊重这一公益资源,只让真正需要的人用。',
  },
  {
    q: '学校方案可以私有部署吗?',
    a: '可以。¥999/月含云端托管,私有部署需另议(通常一次性 ¥30,000 起 + ¥5,000/月维护)。',
  },
  {
    q: 'CoPiano 用什么 MIDI 设备?',
    a: '任何 USB MIDI 键盘都可(雅马哈/Casio/Roland 等)。Web 端通过 Web MIDI API 实时连接,iOS 端通过 Lightning/USB-C 转接。',
  },
  {
    q: '数据隐私怎么处理?',
    a: '录音文件加密存储在 MinIO(国内服务器,符合等保 2.0 三级)。不分享给第三方,删除账号后 30 天内永久删除。',
  },
] as const;

/** 格式化价格(分 → 元) */
export function formatCny(cents: number, cycle: BillingCycle = 'monthly'): string {
  if (cents === 0) return '免费';
  const yuan = cents / 100;
  return `¥${yuan.toFixed(0)}${cycle === 'monthly' ? '/月' : '/年'}`;
}

/** 找 tier by id */
export function getTierById(id: PricingTier['id']): PricingTier | undefined {
  return PRICING_TIERS.find((t) => t.id === id);
}
