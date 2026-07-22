/**
 * 视奏训练 API 类型 — 与后端 schemas/sight_reading.py 对齐
 */

export type SightReadingLevel = 1 | 2 | 3 | 4;
export type SightReadingMode = 'staff' | 'numbered' | 'dual';

export interface SightReadingQuestion {
  id: string;
  /** 题目序号 (1-20) */
  index: number;
  /** 五线谱表示 (MIDI 音符序列,用于 staff/dual 模式) */
  notes_midi: number[];
  /** 简谱表示 (1-7 for do-ti, 用于 numbered/dual 模式) */
  notes_solfege: string[];
  /** 4 个选项 (MIDI 音高) */
  options: number[];
  /** 时值(拍数) */
  duration_beats: number;
  /** 题干文字 */
  prompt?: string;
}

export interface SightReadingAnswer {
  question_id: string;
  selected_midi: number;
  correct: boolean;
  correct_midi: number;
  time_taken_ms: number;
}

export interface SightReadingSession {
  id: string;
  user_id: string;
  level: SightReadingLevel;
  mode: SightReadingMode;
  /** 全部题目 (1-20 题) */
  questions: SightReadingQuestion[];
  /** 已答题目 (含结果) */
  answers: SightReadingAnswer[];
  /** 当前题目索引 (0-based) */
  current_index: number;
  /** 累计正确数 */
  correct_count: number;
  /** 是否结束(20 题答完) */
  finished: boolean;
  /** ISO datetime */
  started_at: string;
  finished_at?: string;
}

export const LEVEL_META: Record<
  SightReadingLevel,
  { label: string; description: string; emoji: string }
> = {
  1: {
    label: '入门',
    description: '单音识别,五线谱 1 个音',
    emoji: '🌱',
  },
  2: {
    label: '初级',
    description: '2-3 音短旋律,简单节奏',
    emoji: '🎵',
  },
  3: {
    label: '中级',
    description: '4-6 音旋律,带附点/切分',
    emoji: '🎶',
  },
  4: {
    label: '高级',
    description: '8+ 音,复调片段,转调',
    emoji: '🎼',
  },
};

export const MODE_META: Record<
  SightReadingMode,
  { label: string; description: string; emoji: string }
> = {
  staff: {
    label: '五线谱',
    description: '标准五线谱 (G 谱号)',
    emoji: '🎼',
  },
  numbered: {
    label: '简谱',
    description: '简谱 1-7 (do-ti)',
    emoji: '🔢',
  },
  dual: {
    label: '双行',
    description: '五线谱 + 简谱对照',
    emoji: '📑',
  },
};

/** MIDI → solfege + 中央 C 上下 八度标记 */
const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
const SOLFEGE_BASE = ['do', 'do#', 're', 're#', 'mi', 'fa', 'fa#', 'sol', 'sol#', 'la', 'la#', 'ti'];

export function midiToNoteName(midi: number): string {
  const note = NOTE_NAMES[midi % 12] ?? '?';
  const octave = Math.floor(midi / 12) - 1;
  return `${note}${octave}`;
}

export function midiToSolfege(midi: number): string {
  // 中央 C = MIDI 60 = do
  return SOLFEGE_BASE[midi % 12] ?? '?';
}
