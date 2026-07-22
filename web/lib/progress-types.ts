/**
 * Progress 页类型 — 由 Evaluation 历史聚合而成
 */

import type { Dimension, Evaluation } from '@/lib/evaluation-types';

export type RangeKey = '7d' | '30d' | '90d' | 'all';

export const RANGE_OPTIONS: { key: RangeKey; label: string; days: number | null }[] = [
  { key: '7d', label: '近 7 天', days: 7 },
  { key: '30d', label: '近 30 天', days: 30 },
  { key: '90d', label: '近 90 天', days: 90 },
  { key: 'all', label: '全部', days: null },
];

/** 一个时间点(横轴) */
export interface ProgressPoint {
  /** 评估 ID */
  id: string;
  /** ISO date (用作横轴标签) */
  date: string;
  /** 显示用日期 MM-DD */
  label: string;
  /** 5 维分 */
  scores: Record<Dimension, number>;
  /** 加权总分 */
  overall: number;
}

export interface DimensionSummary {
  dimension: Dimension;
  avg: number;
  peak: number;
  latest: number;
  /** 较首次的提升 (latest - first),可以为负 */
  delta: number;
}

export function evaluationsToPoints(evaluations: Evaluation[]): ProgressPoint[] {
  return [...evaluations]
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
    .map((ev) => {
      const d = new Date(ev.created_at);
      const label = `${d.getMonth() + 1}/${d.getDate()}`;
      return {
        id: ev.id,
        date: ev.created_at,
        label,
        scores: {
          pitch: ev.scores.pitch?.score ?? 0,
          expressiveness: ev.scores.expressiveness?.score ?? 0,
          hand_pose: ev.scores.hand_pose?.score ?? 0,
          rhythm: ev.scores.rhythm?.score ?? 0,
          sight_reading: ev.scores.sight_reading?.score ?? 0,
        },
        overall: ev.overall,
      };
    });
}

export function summarize(points: ProgressPoint[]): DimensionSummary[] {
  if (points.length === 0) return [];
  const dims: Dimension[] = ['pitch', 'expressiveness', 'hand_pose', 'rhythm', 'sight_reading'];
  return dims.map((dim) => {
    const values = points.map((p) => p.scores[dim]);
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    const peak = Math.max(...values);
    const latest = values[values.length - 1] ?? 0;
    const first = values[0] ?? 0;
    return {
      dimension: dim,
      avg: Math.round(avg),
      peak: Math.round(peak),
      latest: Math.round(latest),
      delta: Math.round(latest - first),
    };
  });
}

export function filterByRange(points: ProgressPoint[], range: RangeKey): ProgressPoint[] {
  const opt = RANGE_OPTIONS.find((o) => o.key === range);
  if (!opt?.days) return points;
  const cutoff = Date.now() - opt.days * 24 * 60 * 60 * 1000;
  return points.filter((p) => new Date(p.date).getTime() >= cutoff);
}
