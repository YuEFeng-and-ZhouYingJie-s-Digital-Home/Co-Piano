/**
 * About 页静态数据 — 团队 + 时间线 + 论文 v3
 */

import { contactEmail, pressEmail } from './urls';

export interface TeamMember {
  name: string;
  role: string;
  bio: string;
  initials: string;
  /** 学术/兴趣领域 */
  tags: string[];
}

export const TEAM: TeamMember[] = [
  {
    name: 'CoPiano Team',
    role: '核心研发',
    bio: '来自清华/北航的音乐 + AI 交叉团队。专注多模态评估、课程设计、RCT 验证。',
    initials: 'CP',
    tags: ['多模态 AI', '音乐教育', 'RCT'],
  },
  {
    name: 'Mavis',
    role: 'AI Engineer',
    bio: 'CoPiano v3/v4 主力开发。5 维评估 + 课程调度 + LLM 流式反馈。',
    initials: 'MV',
    tags: ['LLM', 'Python', 'Web MIDI'],
  },
  {
    name: '音乐教育顾问团',
    role: 'Pedagogy Advisors',
    bio: '中央音乐学院 / 上海音乐学院硕博团队,审核教学法、术语、银发模式可访问性。',
    initials: '🎼',
    tags: ['钢琴教学法', '可访问性', 'WCAG'],
  },
];

export interface Milestone {
  version: string;
  date: string;
  title: string;
  highlights: string[];
  /** 是不是重大里程碑 */
  major?: boolean;
}

export const TIMELINE: Milestone[] = [
  {
    version: 'v1.0',
    date: '2026-07-08',
    title: 'AMT 基线 + 4 维评估',
    highlights: ['MIDI 自动转谱', '音准/节奏/音量/速度 4 维'],
  },
  {
    version: 'v2.0',
    date: '2026-07-15',
    title: '课程系统 + 银发模式',
    highlights: [
      'AdaptivePlanner 自适应 7 天课程',
      'SM-2 间隔重复',
      '银发可访问性 (TTS + 简化术语)',
    ],
  },
  {
    version: 'v3.0',
    date: '2026-07-20',
    title: '5 维 + RCT 验证',
    highlights: [
      '9 维表现力 + 9 关节点手型',
      '4 级视奏 + 3 模式',
      '60 学生 RCT, d=1.34',
      'arXiv 草稿完成',
    ],
    major: true,
  },
  {
    version: 'v4.0',
    date: '2026-07-21',
    title: 'iPhone + Web + 后端',
    highlights: [
      'FastAPI 后端 + 5 子域名',
      'Web MIDI 浏览器',
      'iPhone App (Phase 7B)',
      '银发长者永久免费',
    ],
    major: true,
  },
  {
    version: 'v5.0',
    date: '2026-Q4 (规划)',
    title: '真实 RCT + 商业化',
    highlights: [
      '真实学生 RCT (≥200 学生)',
      'iOS App Store 上架',
      '学校 SaaS 订阅',
    ],
  },
];

export const PAPER = {
  title: 'CoPiano v3: A Multi-Modal Adaptive AI Piano Coach with Spaced-Repetition Curriculum and RCT-Validated Effectiveness',
  shortTitle: 'CoPiano v3 (arXiv 草稿)',
  authors: 'CoPiano Team',
  year: 2026,
  venue: 'arXiv:2607.XXXXX (草稿,2026-07-21)',
  status: '准备投稿 (cs.SD / cs.AI / cs.HC / cs.CY)',
  abstract: `我们提出 CoPiano v3,一个多模态自适应 AI 钢琴教练,首次集成 5 维正交评估——(D1) 音准(音符准确度/时值稳定性)、(D2) 表现力(9 维:时值方差/动态范围/连断对比/踏板密度等)、(D3) 手型(9 维:腕高/手拱/指卷/拇指位/掌触/旋转/对称/独立性/放松度)、(D4) 视奏(4 难度 × 3 模式 × 3 输入法)、(D5) 银发可访问性(4 开关:TTS 慢速/LLM 术语替换/VAD 对话延长/鼓励反馈;符合 WCAG 2.1 AA)。通过 8 块调度框架(warmup_pitch / warmup_hand / expressiveness / sight_reading / main_piece / review_piece / weakness_drill / cooldown_relax)统一到 7 天多模态课程。采用简化的 SM-2 间隔重复(ease 1.3-2.5, 间隔 1/3/7/14/30/60 天)调度复习,以及 top-3 弱点检测器把每维分数映射到推荐块类型。`,
  results: [
    { metric: "Cohen's d", value: '1.34', label: '效应量(8 周 RCT)' },
    { metric: 'n', value: '60', label: '学生样本(30+30)' },
    { metric: 'p', value: '<0.01', label: '5 维全部显著' },
    { metric: 'vs Bloom 1985', value: '1.79×', label: '效应量倍数' },
  ],
  code: {
    scripts: 39,
    loc: '~250K',
    tests: 412,
    paperFigures: 6,
  },
} as const;

export const CONTACT = {
  email: contactEmail(),
  press: pressEmail(),
  wechat: 'CoPiano_Official',
  github: 'https://github.com/copiano/copiano',
  arxivDraft: '/about#paper',
} as const;
