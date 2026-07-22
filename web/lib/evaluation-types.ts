/**
 * 5 维评估 API 类型 — 与后端 schemas/evaluation.py 对齐
 */

export type Dimension = 'pitch' | 'expressiveness' | 'hand_pose' | 'rhythm' | 'sight_reading';

export interface DimensionScore {
  /** 0-100 */
  score: number;
  /** 子维度详情 (可选) */
  breakdown?: Record<string, number>;
  /** 该维度的文字反馈 */
  feedback?: string;
}

export interface Evaluation {
  id: string;
  user_id: string;
  /** ISO datetime */
  created_at: string;
  /** 关联的 block (来自 curriculum) */
  block_id?: string;
  /** 参考曲目 ID(可选) */
  reference_id?: string;
  /** 5 维分项 */
  scores: Record<Dimension, DimensionScore>;
  /** 总分 0-100,5 维加权 (pitch 0.20 + expr 0.25 + hand 0.20 + rhythm 0.20 + sr 0.15) */
  overall: number;
  /** LLM 反馈 (可选,POST /feedback 后才有) */
  feedback_text?: string;
  /** 录音 MIDI 在 MinIO 的 key */
  midi_key?: string;
  /** 评估模型版本 */
  model_version: string;
  /** 评估耗时 (ms) */
  latency_ms: number;
}

export const DIMENSION_META: Record<
  Dimension,
  { label: string; emoji: string; color: string; weight: number }
> = {
  pitch: { label: '音准', emoji: '🎯', color: 'text-piano-500', weight: 0.2 },
  expressiveness: { label: '表现力', emoji: '🎨', color: 'text-purple-500', weight: 0.25 },
  hand_pose: { label: '手型', emoji: '✋', color: 'text-amber-500', weight: 0.2 },
  rhythm: { label: '节奏', emoji: '🥁', color: 'text-blue-500', weight: 0.2 },
  sight_reading: { label: '视奏', emoji: '👀', color: 'text-green-500', weight: 0.15 },
};

export const DIMENSIONS_ORDER: Dimension[] = [
  'pitch',
  'expressiveness',
  'hand_pose',
  'rhythm',
  'sight_reading',
];
