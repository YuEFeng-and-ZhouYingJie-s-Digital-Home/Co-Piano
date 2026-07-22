'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { StaffDisplay } from '@/components/sight-reading/staff-display';

interface MidiStaffPreviewProps {
  /** MIDI URL (presigned from MinIO) */
  midiUrl: string;
  /** 标题 */
  title?: string;
}

/**
 * 从后端拉取 MIDI 文件并解析为音符序列,然后用 VexFlow 渲染
 * 限制:最多显示前 32 音(避免 SVG 太大)
 */
export function MidiStaffPreview({ midiUrl, title = '演奏谱面' }: MidiStaffPreviewProps) {
  const [notes, setNotes] = useState<number[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const res = await fetch(midiUrl);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const buf = await res.arrayBuffer();
        const parsed = parseMidiToPitches(buf);
        if (!cancelled) {
          setNotes(parsed.slice(0, 32));
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : '无法加载');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [midiUrl]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>
          {loading && '加载 MIDI...'}
          {error && `加载失败: ${error}`}
          {notes && `共 ${notes.length} 个音符${notes.length === 32 ? ' (显示前 32)' : ''}`}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {notes && notes.length > 0 ? (
          <StaffDisplay notesMidi={notes} width={500} height={140} />
        ) : (
          !loading && !error && (
            <p className="text-sm text-muted-foreground text-center py-6">
              暂无音符数据
            </p>
          )
        )}
      </CardContent>
    </Card>
  );
}

/**
 * 极简 SMF 解析器 — 只取 Note On 事件的 pitch
 * 足够给五线谱显示用,不解析 duration / velocity
 */
function parseMidiToPitches(buf: ArrayBuffer): number[] {
  const bytes = new Uint8Array(buf);
  if (
    bytes.length < 14 ||
    bytes[0] !== 0x4d || // M
    bytes[1] !== 0x54 || // T
    bytes[2] !== 0x68 || // h
    bytes[3] !== 0x64    // d
  ) {
    throw new Error('不是有效的 MIDI 文件');
  }

  // 跳过 header(14 bytes)到第一个 track
  let i = 14;
  const pitches: number[] = [];
  // running status 初始 0
  let runningStatus = 0;

  while (i < bytes.length) {
    // 找 "MTrk"
    if (
      i + 8 <= bytes.length &&
      bytes[i] === 0x4d &&
      bytes[i + 1] === 0x54 &&
      bytes[i + 2] === 0x72 &&
      bytes[i + 3] === 0x6b
    ) {
      // 读 track 长度
      const trackLen =
        (bytes[i + 4]! << 24) |
        (bytes[i + 5]! << 16) |
        (bytes[i + 6]! << 8) |
        bytes[i + 7]!;
      const trackEnd = i + 8 + trackLen;
      i += 8;

      // 解析 track 内的 events
      while (i < trackEnd && i < bytes.length) {
        // 读 VLQ delta
        let delta = 0;
        let cont = true;
        while (cont && i < trackEnd) {
          const b = bytes[i++]!;
          delta = (delta << 7) | (b & 0x7f);
          if ((b & 0x80) === 0) cont = false;
        }

        if (i >= trackEnd) break;
        let status = bytes[i]!;

        // running status
        if (status < 0x80) {
          status = runningStatus;
        } else {
          runningStatus = status;
          i++;
        }

        const cmd = status & 0xf0;
        if (cmd === 0x90) {
          // Note On
          const pitch = bytes[i++]!;
          const vel = bytes[i++]!;
          if (vel > 0) {
            pitches.push(pitch);
          }
        } else if (cmd === 0x80) {
          i += 2; // Note Off
        } else if (cmd === 0xa0 || cmd === 0xb0 || cmd === 0xe0) {
          i += 2; // 2 data bytes
        } else if (cmd === 0xc0 || cmd === 0xd0) {
          i += 1; // 1 data byte
        } else if (status === 0xff) {
          // Meta event
          i++; // type
          // 读 length VLQ
          let metaLen = 0;
          let cont2 = true;
          while (cont2 && i < trackEnd) {
            const b = bytes[i++]!;
            metaLen = (metaLen << 7) | (b & 0x7f);
            if ((b & 0x80) === 0) cont2 = false;
          }
          i += metaLen;
        } else if (status === 0xf0 || status === 0xf7) {
          // Sysex
          let sysexLen = 0;
          let cont3 = true;
          while (cont3 && i < trackEnd) {
            const b = bytes[i++]!;
            sysexLen = (sysexLen << 7) | (b & 0x7f);
            if ((b & 0x80) === 0) cont3 = false;
          }
          i += sysexLen;
        } else {
          // 未知 - 跳过
          i += 2;
        }
      }
      i = trackEnd;
    } else {
      i++;
    }
  }
  return pitches;
}
