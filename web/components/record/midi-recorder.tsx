'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Mic, Square, Loader2, AlertCircle, CheckCircle2, Upload, Music } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { api, ApiError } from '@/lib/api';
import { encodeSMF, type RecordedNote } from '@/lib/midi-encoder';
import { EvaluationResult } from '@/components/record/evaluation-result';
import type { Evaluation } from '@/lib/evaluation-types';
import { cn } from '@/lib/utils';

type RecorderState = 'idle' | 'requesting' | 'ready' | 'recording' | 'uploading' | 'done' | 'error';

interface MidiDevice {
  id: string;
  name: string;
  manufacturer: string;
}

export function MidiRecorder() {
  const router = useRouter();
  const [state, setState] = useState<RecorderState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [devices, setDevices] = useState<MidiDevice[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [noteCount, setNoteCount] = useState(0);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);

  const accessRef = useRef<MIDIAccess | null>(null);
  const notesRef = useRef<RecordedNote[]>([]);
  const activeNotesRef = useRef<Map<number, number>>(new Map()); // pitch -> startMs
  const startTimeRef = useRef<number>(0);
  const timerRef = useRef<number | null>(null);
  const inputRef = useRef<MIDIInput | null>(null);

  // 请求 MIDI 权限
  const requestMidi = useCallback(async () => {
    if (typeof navigator === 'undefined' || !navigator.requestMIDIAccess) {
      setError('你的浏览器不支持 Web MIDI API。请使用 Chrome / Edge / Opera 桌面版。');
      setState('error');
      return;
    }
    setState('requesting');
    setError(null);
    try {
      const access = await navigator.requestMIDIAccess({ sysex: false });
      accessRef.current = access;
      const inputs: MidiDevice[] = [];
      access.inputs.forEach((input) => {
        inputs.push({
          id: input.id,
          name: input.name ?? 'Unknown MIDI Device',
          manufacturer: input.manufacturer ?? '',
        });
      });
      setDevices(inputs);
      if (inputs.length === 0) {
        setError('没有检测到 MIDI 设备。请连接键盘后点击"重新检测"。');
        setState('error');
        return;
      }
      setSelectedDevice(inputs[0]?.id ?? null);
      setState('ready');
    } catch (e) {
      setError('MIDI 权限被拒绝,或浏览器不支持。');
      setState('error');
    }
  }, []);

  // 绑定当前选中的 input
  useEffect(() => {
    if (!accessRef.current || !selectedDevice) return;
    const access = accessRef.current;
    if (inputRef.current) {
      inputRef.current.onmidimessage = null;
    }
    const input = access.inputs.get(selectedDevice);
    if (!input) return;
    inputRef.current = input;
    input.onmidimessage = (event: MIDIMessageEvent) => {
      if (!event.data) return;
      const [status, pitch, velocity] = event.data;
      if (status === undefined || pitch === undefined) return;
      const cmd = status & 0xf0;
      const now = performance.now() - startTimeRef.current;
      if (cmd === 0x90 && velocity && velocity > 0) {
        // Note On
        activeNotesRef.current.set(pitch, now);
        setNoteCount((c) => c + 1);
      } else if (cmd === 0x80 || (cmd === 0x90 && velocity === 0)) {
        // Note Off
        const start = activeNotesRef.current.get(pitch);
        if (start !== undefined) {
          notesRef.current.push({
            pitch,
            startMs: start,
            durationMs: Math.max(50, now - start),
            velocity: velocity ?? 80,
          });
          activeNotesRef.current.delete(pitch);
        }
      }
    };
  }, [selectedDevice]);

  // 设备插拔监听
  useEffect(() => {
    if (!accessRef.current) return;
    const access = accessRef.current;
    const onStateChange = () => {
      const inputs: MidiDevice[] = [];
      access.inputs.forEach((input) => {
        inputs.push({
          id: input.id,
          name: input.name ?? 'Unknown MIDI Device',
          manufacturer: input.manufacturer ?? '',
        });
      });
      setDevices(inputs);
    };
    access.onstatechange = onStateChange;
    return () => {
      access.onstatechange = null;
    };
  }, [state]);

  // 计时器
  useEffect(() => {
    if (state !== 'recording') return;
    timerRef.current = window.setInterval(() => {
      setElapsedMs(performance.now() - startTimeRef.current);
    }, 100);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [state]);

  const startRecording = () => {
    if (state !== 'ready') return;
    notesRef.current = [];
    activeNotesRef.current.clear();
    setNoteCount(0);
    setElapsedMs(0);
    startTimeRef.current = performance.now();
    setState('recording');
  };

  const stopAndUpload = async () => {
    if (state !== 'recording') return;
    setState('uploading');

    // 关闭还在 active 的音符
    const now = performance.now() - startTimeRef.current;
    activeNotesRef.current.forEach((start, pitch) => {
      notesRef.current.push({
        pitch,
        startMs: start,
        durationMs: Math.max(50, now - start),
        velocity: 80,
      });
    });
    activeNotesRef.current.clear();

    if (notesRef.current.length === 0) {
      setError('没有录到任何音符,请重试。');
      setState('error');
      return;
    }

    try {
      const midiBytes = encodeSMF(notesRef.current);
      const blob = new Blob([midiBytes as BlobPart], { type: 'audio/midi' });
      const formData = new FormData();
      formData.append('midi', blob, 'recording.mid');
      formData.append('duration_ms', String(Math.round(now)));

      const ev = await api.upload<Evaluation>('/api/v1/evaluations', formData);
      setEvaluation(ev);
      setState('done');
      router.refresh();
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`评估失败: ${e.detail}`);
      } else {
        setError('上传或评估失败,请重试');
      }
      setState('error');
    }
  };

  const reset = () => {
    setEvaluation(null);
    setError(null);
    setNoteCount(0);
    setElapsedMs(0);
    setState(devices.length > 0 ? 'ready' : 'idle');
  };

  // 已完成 → 显示结果
  if (state === 'done' && evaluation) {
    return (
      <div className="space-y-4">
        <Alert>
          <CheckCircle2 className="h-4 w-4" />
          <AlertTitle>评估完成</AlertTitle>
          <AlertDescription>
            耗时 {evaluation.latency_ms}ms · 模型 {evaluation.model_version} · 总分{' '}
            <strong>{Math.round(evaluation.overall)}</strong>
          </AlertDescription>
        </Alert>
        <EvaluationResult evaluation={evaluation} />
        <div className="flex gap-2">
          <Button onClick={reset} variant="piano">
            再录一次
          </Button>
          <Button asChild variant="outline">
            <a href="/app/feedback">查看历史反馈</a>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 设备选择 */}
      {state === 'idle' && (
        <Card>
          <CardContent className="pt-6 text-center">
            <Music className="mx-auto h-12 w-12 text-piano-500" />
            <h3 className="mt-3 text-lg font-semibold">Web MIDI 录音</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              连接 MIDI 键盘后,点击下方按钮开始。
            </p>
            <Button onClick={requestMidi} variant="piano" className="mt-4">
              <Mic className="mr-2 h-4 w-4" />
              检测 MIDI 设备
            </Button>
          </CardContent>
        </Card>
      )}

      {state === 'requesting' && (
        <Card>
          <CardContent className="pt-6 flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            正在请求 MIDI 权限...
          </CardContent>
        </Card>
      )}

      {state === 'ready' && (
        <Card>
          <CardContent className="pt-6 space-y-4">
            <div>
              <label className="text-sm font-medium">选择设备</label>
              {devices.length > 1 ? (
                <select
                  value={selectedDevice ?? ''}
                  onChange={(e) => setSelectedDevice(e.target.value)}
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  {devices.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} {d.manufacturer && `(${d.manufacturer})`}
                    </option>
                  ))}
                </select>
              ) : (
                <div className="mt-1 text-sm text-muted-foreground">
                  ✓ {devices[0]?.name}
                </div>
              )}
            </div>
            <Button onClick={startRecording} variant="piano" size="lg" className="w-full">
              <Mic className="mr-2 h-5 w-5" />
              开始录音
            </Button>
          </CardContent>
        </Card>
      )}

      {state === 'recording' && (
        <Card className="border-red-500/40">
          <CardContent className="pt-6 text-center space-y-4">
            <div className="flex items-center justify-center gap-2 text-red-500">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-75" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500" />
              </span>
              <span className="font-medium">录音中</span>
            </div>
            <div className="text-4xl font-mono font-bold tabular-nums">
              {formatTime(elapsedMs)}
            </div>
            <div className="text-sm text-muted-foreground">
              已录 {noteCount} 个音符
            </div>
            <Button onClick={stopAndUpload} variant="destructive" size="lg" className="w-full">
              <Square className="mr-2 h-4 w-4" />
              停止并评估
            </Button>
          </CardContent>
        </Card>
      )}

      {state === 'uploading' && (
        <Card>
          <CardContent className="pt-6 flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            上传 MIDI 并调用 5 维 AI 评估...
          </CardContent>
        </Card>
      )}

      {state === 'error' && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>出错了</AlertTitle>
          <AlertDescription>
            {error}
            <div className="mt-2 flex gap-2">
              <Button size="sm" variant="outline" onClick={reset}>
                重试
              </Button>
              <MidiFileUploader onUploaded={(ev) => { setEvaluation(ev); setState('done'); }} />
            </div>
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}

function formatTime(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

/** 备用:直接上传 .mid 文件(没 MIDI 键盘时) */
function MidiFileUploader({ onUploaded }: { onUploaded: (e: Evaluation) => void }) {
  const [pending, setPending] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const onFile = async (file: File) => {
    setPending(true);
    try {
      const fd = new FormData();
      fd.append('midi', file);
      const ev = await api.upload<Evaluation>('/api/v1/evaluations', fd);
      onUploaded(ev);
    } catch (e) {
      console.error('Upload failed:', e);
      alert('上传失败');
    } finally {
      setPending(false);
    }
  };

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept=".mid,.midi,audio/midi,audio/x-midi"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onFile(f);
        }}
      />
      <Button
        size="sm"
        variant="outline"
        disabled={pending}
        onClick={() => inputRef.current?.click()}
      >
        {pending ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : <Upload className="mr-1 h-3 w-3" />}
        上传 MIDI 文件
      </Button>
    </>
  );
}
