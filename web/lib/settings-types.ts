/**
 * Settings / User API 类型
 */

export type Plan = 'free' | 'pro' | 'senior' | 'teacher' | 'school';

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  /** 银发模式 */
  is_senior: boolean;
  /** 当前订阅档位 */
  plan: Plan;
  /** 订阅到期日 (Pro/Teacher/School 才有) */
  plan_expires_at?: string;
  /** 创建时间 */
  created_at: string;
}

export const PLAN_META: Record<Plan, { label: string; emoji: string; color: string }> = {
  free: { label: 'Free', emoji: '🆓', color: 'text-muted-foreground' },
  pro: { label: 'Pro', emoji: '⭐', color: 'text-piano-500' },
  senior: { label: '银发公益', emoji: '❤️', color: 'text-pink-500' },
  teacher: { label: 'Teacher', emoji: '👨‍🏫', color: 'text-blue-500' },
  school: { label: 'School', emoji: '🏫', color: 'text-indigo-500' },
};
