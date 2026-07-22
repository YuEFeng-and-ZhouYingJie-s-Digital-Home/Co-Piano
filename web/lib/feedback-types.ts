/**
 * LLM 反馈 API 类型 — 与后端 schemas/feedback.py 对齐
 */

export interface Feedback {
  id: string;
  evaluation_id: string;
  /** LLM 反馈正文 */
  text: string;
  /** 使用的模型 (qwen2.5-7b / gpt-4o-mini / etc.) */
  model: string;
  /** 反馈生成耗时 (ms) */
  latency_ms: number;
  /** 是否针对银发用户简化 */
  simplified_for_senior: boolean;
  /** ISO datetime */
  created_at: string;
}

export interface FeedbackListItem {
  evaluation_id: string;
  feedback_id?: string;
  overall: number;
  /** 5 维简版 */
  top_dim: string;
  bottom_dim: string;
  /** 评估时间 */
  evaluated_at: string;
  /** 反馈生成时间 (有反馈才有) */
  feedback_at?: string;
  /** 反馈是否生成 */
  has_feedback: boolean;
}

export const SENIOR_KEYWORDS_TO_SIMPLIFY = [
  'terminus',
  'ritardando',
  'accelerando',
  'pianissimo',
  'fortissimo',
  'sforzando',
  'subito',
  'diminuendo',
  'crescendo',
  'staccato',
  'legato',
  'tenuto',
  'marcato',
  'sempre',
  'poco',
  'molto',
  'simile',
  'segue',
];
