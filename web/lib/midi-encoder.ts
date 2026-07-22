/**
 * SMF (Standard MIDI File) 编码器 — 极简版,只支持 Format 0 / 单轨
 * 足够把 Web MIDI 录到的 Note On/Off 编成 .mid buffer 上传
 */

/** Variable-Length Quantity 编码 (MIDI tick delta 标准) */
export function encodeVLQ(n: number): number[] {
  if (n < 0) throw new Error('VLQ must be non-negative');
  if (n === 0) return [0];
  const bytes: number[] = [];
  bytes.push(n & 0x7f);
  n >>= 7;
  while (n > 0) {
    bytes.push((n & 0x7f) | 0x80);
    n >>= 7;
  }
  return bytes.reverse();
}

/** int32 big-endian 编码 */
function int32BE(n: number): number[] {
  return [(n >> 24) & 0xff, (n >> 16) & 0xff, (n >> 8) & 0xff, n & 0xff];
}

/** int16 big-endian 编码 */
function int16BE(n: number): number[] {
  return [(n >> 8) & 0xff, n & 0xff];
}

export interface RecordedNote {
  /** MIDI note number 0-127 */
  pitch: number;
  /** 起始时间 (ms from recording start) */
  startMs: number;
  /** 持续时间 (ms) */
  durationMs: number;
  /** 力度 0-127,默认 80 */
  velocity: number;
}

/**
 * 把录到的音符列表编成 SMF Format 0 buffer (Uint8Array)
 * 480 ticks per quarter note (PPQ)
 */
export function encodeSMF(notes: RecordedNote[], ppq = 480): Uint8Array {
  // 计算每个事件绝对时间(tick),然后转为 delta
  type Event = { tick: number; bytes: number[] };
  const events: Event[] = [];
  for (const n of notes) {
    const startTick = Math.round((n.startMs / 1000) * ppq * 2); // 假设 120 BPM
    const endTick = startTick + Math.round((n.durationMs / 1000) * ppq * 2);
    const vel = Math.min(127, Math.max(1, n.velocity));

    events.push({
      tick: startTick,
      bytes: [0x90, n.pitch & 0x7f, vel],
    });
    events.push({
      tick: endTick,
      bytes: [0x80, n.pitch & 0x7f, 0],
    });
  }

  // 按 tick 排序
  events.sort((a, b) => a.tick - b.tick);

  // 转为 delta time
  const trackBytes: number[] = [];
  let prevTick = 0;
  for (const e of events) {
    const delta = e.tick - prevTick;
    trackBytes.push(...encodeVLQ(delta), ...e.bytes);
    prevTick = e.tick;
  }
  // End of Track event
  trackBytes.push(0x00, 0xff, 0x2f, 0x00);

  // Header chunk
  const header: number[] = [
    0x4d, 0x54, 0x68, 0x64, // "MThd"
    ...int32BE(6), // chunk length
    ...int16BE(0), // format 0
    ...int16BE(1), // 1 track
    ...int16BE(ppq), // ticks per quarter
  ];

  // Track chunk
  const trackHeader = [0x4d, 0x54, 0x72, 0x6b, ...int32BE(trackBytes.length)];

  return new Uint8Array([...header, ...trackHeader, ...trackBytes]);
}
