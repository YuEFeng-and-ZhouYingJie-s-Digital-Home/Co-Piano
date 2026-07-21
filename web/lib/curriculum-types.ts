/**
 * Curriculum API 类型 — 与后端 schemas/curriculum.py 对齐
 */

export type BlockType =
  | 'warmup_pitch'
  | 'warmup_hand'
  | 'expressiveness'
  | 'sight_reading'
  | 'main_piece'
  | 'review_piece'
  | 'weakness_drill'
  | 'cooldown_relax';

export type DimensionName = 'pitch' | 'expressiveness' | 'hand_pose' | 'rhythm' | 'sight_reading';

export interface CurriculumBlock {
  id: string;
  block_type: BlockType;
  title: string;
  description?: string;
  duration_min: number;
  order: number;
  /** 该 block 关联的 MIDI 曲目或练习 ID */
  piece_id?: string;
  /** 已完成? */
  completed: boolean;
  /** 完成时分数(0-100,SM-2) */
  score?: number;
}

export interface CurriculumDay {
  day_num: number;
  /** ISO date */
  date: string;
  title: string;
  focus_dimension?: DimensionName;
  blocks: CurriculumBlock[];
  /** 该天总时长(分钟) */
  total_min: number;
  /** 全部完成? */
  completed: boolean;
}

export interface CurriculumWeek {
  /** 用户当前在第几天(1-7) */
  current_day: number;
  days: CurriculumDay[];
  /** 整体完成度 0-1 */
  completion_ratio: number;
  /** 本周统计 */
  stats: {
    blocks_total: number;
    blocks_done: number;
    minutes_total: number;
    minutes_done: number;
  };
}

/** Block 中文 label + 图标映射 */
export const BLOCK_META: Record<
  BlockType,
  { label: string; emoji: string; color: string }
> = {
  warmup_pitch: { label: '音准热身', emoji: '🎯', color: 'text-piano-500' },
  warmup_hand: { label: '手型热身', emoji: '✋', color: 'text-amber-500' },
  expressiveness: { label: '表现力训练', emoji: '🎨', color: 'text-purple-500' },
  sight_reading: { label: '视奏练习', emoji: '👀', color: 'text-green-500' },
  main_piece: { label: '主曲目', emoji: '🎹', color: 'text-piano-700' },
  review_piece: { label: '复习曲目', emoji: '🔁', color: 'text-blue-500' },
  weakness_drill: { label: '弱点训练', emoji: '💪', color: 'text-red-500' },
  cooldown_relax: { label: '放松收尾', emoji: '🌙', color: 'text-indigo-500' },
};

export const DIMENSION_META: Record<DimensionName, { label: string; emoji: string }> = {
  pitch: { label: '音准', emoji: '🎯' },
  expressiveness: { label: '表现力', emoji: '🎨' },
  hand_pose: { label: '手型', emoji: '✋' },
  rhythm: { label: '节奏', emoji: '🥁' },
  sight_reading: { label: '视奏', emoji: '👀' },
};
