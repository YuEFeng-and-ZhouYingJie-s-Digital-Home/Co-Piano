/**
 * /app 子导航 — 单一数据源,sidebar 和 mobile nav 都从这里读
 */
import {
  Home,
  BookOpen,
  Mic,
  History,
  TrendingUp,
  Eye,
  Settings,
  type LucideIcon,
} from 'lucide-react';

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  description?: string;
  /** 移动端底部 tab 排序,小屏只显示前 5 */
  primary?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  {
    href: '/app',
    label: '首页',
    icon: Home,
    description: '今日概览 + 推荐',
    primary: true,
  },
  {
    href: '/app/curriculum',
    label: '课程',
    icon: BookOpen,
    description: '7 天自适应课程',
    primary: true,
  },
  {
    href: '/app/record',
    label: '录音',
    icon: Mic,
    description: 'Web MIDI 评估',
    primary: true,
  },
  {
    href: '/app/feedback',
    label: '反馈',
    icon: History,
    description: '历史评估 + LLM 反馈',
    primary: true,
  },
  {
    href: '/app/progress',
    label: '进度',
    icon: TrendingUp,
    description: '5 维成长曲线',
    primary: true,
  },
  {
    href: '/app/sight-reading',
    label: '视奏',
    icon: Eye,
    description: '4 难度 × 3 模式',
  },
  {
    href: '/app/settings',
    label: '设置',
    icon: Settings,
    description: '账户 / 银发 / 订阅',
  },
];
