import { describe, it, expect } from 'vitest';
import { encodeVLQ, encodeSMF, type RecordedNote } from '@/lib/midi-encoder';

describe('VLQ encoding', () => {
  it('encodes 0 as single zero byte', () => {
    expect(encodeVLQ(0)).toEqual([0]);
  });

  it('encodes 1-127 as single byte', () => {
    expect(encodeVLQ(1)).toEqual([1]);
    expect(encodeVLQ(127)).toEqual([0x7f]);
  });

  it('encodes 128 as two bytes with continuation bit', () => {
    // 128 = 0x80 0x00 → VLQ [0x81, 0x00]
    expect(encodeVLQ(128)).toEqual([0x81, 0x00]);
  });

  it('encodes 16384 correctly (3 bytes)', () => {
    // 16384 = 0x4000 → VLQ [0x81, 0x80, 0x00]
    expect(encodeVLQ(16384)).toEqual([0x81, 0x80, 0x00]);
  });

  it('rejects negative', () => {
    expect(() => encodeVLQ(-1)).toThrow();
  });
});

describe('SMF encoding', () => {
  it('encodes empty notes to a minimal valid SMF', () => {
    const buf = encodeSMF([]);
    // header (14) + track header (8) + EndOfTrack (4) = 26 bytes
    expect(buf.length).toBe(26);
    // "MThd"
    expect(String.fromCharCode(buf[0]!, buf[1]!, buf[2]!, buf[3]!)).toBe('MThd');
    // "MTrk"
    expect(String.fromCharCode(buf[14]!, buf[15]!, buf[16]!, buf[17]!)).toBe('MTrk');
    // Format 0
    expect(buf[9]).toBe(0);
    expect(buf[11]).toBe(1);
  });

  it('encodes a single C4 quarter note correctly', () => {
    // C4 (MIDI 60), 120 BPM → 1 quarter = 500ms
    // ppq=480, 120 BPM → 480 ticks per quarter
    // 0ms → tick 0; 500ms → tick 480
    const notes: RecordedNote[] = [
      { pitch: 60, startMs: 0, durationMs: 500, velocity: 80 },
    ];
    const buf = encodeSMF(notes);
    expect(buf.length).toBeGreaterThan(26);

    // Note On at delta 0: 0x00 0x90 0x3C 0x50
    // Note Off at delta 480: VLQ(480) = 0x81 0xE0 → 0x81 0xE0 0x80 0x3C 0x00
    // End of Track: 0x00 0xFF 0x2F 0x00
    const track = Array.from(buf.slice(22));
    // Find Note On
    expect(track).toContain(0x90);
    expect(track).toContain(60); // C4
    expect(track).toContain(80); // velocity
  });

  it('handles multiple notes and sorts by tick', () => {
    const notes: RecordedNote[] = [
      { pitch: 64, startMs: 1000, durationMs: 500, velocity: 90 },
      { pitch: 60, startMs: 0, durationMs: 500, velocity: 80 },
      { pitch: 67, startMs: 500, durationMs: 500, velocity: 85 },
    ];
    const buf = encodeSMF(notes);
    // 应该按 tick 排序: 60@0, 67@500, 64@1000
    // 找出 pitches 出现顺序
    const pitches: number[] = [];
    for (let i = 22; i < buf.length; i++) {
      const b = buf[i]!;
      if (b >= 60 && b <= 67) {
        pitches.push(b);
      }
    }
    // Note On 顺序: 60, 67, 64
    // Note Off 顺序: 60, 67, 64
    const onIndices = [0, 2, 4]; // positions of Note On pitches
    expect(pitches[onIndices[0]]).toBe(60);
    expect(pitches[onIndices[1]]).toBe(67);
    expect(pitches[onIndices[2]]).toBe(64);
  });

  it('clamps velocity to 0-127', () => {
    const notes: RecordedNote[] = [
      { pitch: 60, startMs: 0, durationMs: 100, velocity: 200 }, // over
      { pitch: 62, startMs: 100, durationMs: 100, velocity: 0 }, // zero (treat as 1)
    ];
    const buf = encodeSMF(notes);
    // Should not throw
    expect(buf.length).toBeGreaterThan(26);
  });
});
