'use client';

import { useEffect, useRef, useState } from 'react';
import { Renderer, Stave, StaveNote, Accidental, Voice, Formatter } from 'vexflow';
import { AlertCircle } from 'lucide-react';

interface StaffDisplayProps {
  /** MIDI 音高列表 (0-127) */
  notesMidi: number[];
  /** 显示宽度 (默认 360) */
  width?: number;
  /** 显示高度 (默认 120) */
  height?: number;
  /** 主题:'light' | 'dark' | 'auto' */
  theme?: 'light' | 'dark' | 'auto';
  /** 是否显示拍号 */
  showTimeSignature?: boolean;
  /** 错误回调 */
  onError?: (e: Error) => void;
}

const NOTE_NAMES_SHARP = ['c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#', 'a', 'a#', 'b'];

/** VexFlow key 转换 (c/4 = 中央 C) */
function midiToVFKey(midi: number): { key: string; accidental?: '#' | 'b' } {
  const noteIndex = midi % 12;
  const octave = Math.floor(midi / 12) - 1;
  const baseKey = NOTE_NAMES_SHARP[noteIndex] ?? 'c';
  if (baseKey.includes('#')) {
    return { key: `${baseKey[0]}/${octave}`, accidental: '#' };
  }
  return { key: `${baseKey}/${octave}` };
}

/**
 * 用 VexFlow 渲染 MIDI 音符序列为标准五线谱
 * 支持 sharp 升降记号自动加
 */
export function StaffDisplay({
  notesMidi,
  width = 360,
  height = 120,
  theme = 'auto',
  showTimeSignature = true,
  onError,
}: StaffDisplayProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    if (notesMidi.length === 0) {
      setError('无音符可显示');
      return;
    }

    try {
      // 清理旧内容
      containerRef.current.innerHTML = '';

      // 决定颜色
      const isDark =
        theme === 'dark' ||
        (theme === 'auto' &&
          typeof window !== 'undefined' &&
          window.matchMedia('(prefers-color-scheme: dark)').matches);
      const strokeColor = isDark ? '#e5e7eb' : '#1f2937';
      const fillColor = isDark ? '#e5e7eb' : '#1f2937';

      const renderer = new Renderer(containerRef.current, Renderer.Backends.SVG);
      renderer.resize(width, height);
      const context = renderer.getContext();
      context.setStrokeStyle(strokeColor);
      context.setFillStyle(fillColor);

      const stave = new Stave(10, 0, width - 20);
      if (showTimeSignature) {
        stave.addClef('treble').addTimeSignature('4/4');
      } else {
        stave.addClef('treble');
      }
      stave.setContext(context).draw();

      // 转换音符
      const staveNotes = notesMidi.map((midi) => {
        const { key, accidental } = midiToVFKey(midi);
        const note = new StaveNote({
          keys: [key],
          duration: 'q',
        });
        if (accidental === '#') {
          note.addModifier(new Accidental('#'), 0);
        }
        return note;
      });

      // 4 音符一音组,自动换行(简化为单组)
      const voice = new Voice({ numBeats: staveNotes.length, beatValue: 4 });
      voice.setStrict(false);
      voice.addTickables(staveNotes);

      new Formatter().joinVoices([voice]).format([voice], width - 60);
      voice.draw(context, stave);
    } catch (e) {
      const err = e instanceof Error ? e : new Error(String(e));
      setError(err.message);
      onError?.(err);
    }
  }, [notesMidi, width, height, theme, showTimeSignature, onError]);

  if (error) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <AlertCircle className="h-4 w-4" />
        五线谱渲染失败: {error}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="mx-auto"
      style={{ width, height }}
      aria-label="五线谱"
    />
  );
}
