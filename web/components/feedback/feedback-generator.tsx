'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Sparkles, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { api, ApiError } from '@/lib/api';
import { auth } from '@/auth';
import type { Feedback } from '@/lib/feedback-types';

interface FeedbackGeneratorProps {
  evaluationId: string;
  initialFeedback?: Feedback | null;
  /** 用户是否启用银发模式 */
  isSenior?: boolean;
}

type Status = 'idle' | 'connecting' | 'streaming' | 'done' | 'error';

export function FeedbackGenerator({
  evaluationId,
  initialFeedback,
  isSenior = false,
}: FeedbackGeneratorProps) {
  const router = useRouter();
  const [status, setStatus] = useState<Status>(initialFeedback ? 'done' : 'idle');
  const [text, setText] = useState<string>(initialFeedback?.text ?? '');
  const [model, setModel] = useState<string | null>(initialFeedback?.model ?? null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const startGeneration = async () => {
    setStatus('connecting');
    setError(null);
    setText('');

    // 1. 先调 POST /api/v1/feedback 触发 LLM 生成(返回 partial)
    try {
      await api.post<{ feedback_id: string }>('/api/v1/feedback', {
        evaluation_id: evaluationId,
        streaming: true,
        senior_simplify: isSenior,
      });
    } catch (e) {
      // 即使后端 fallback,继续尝试 WS
      console.warn('feedback POST failed, trying WS anyway:', e);
    }

    // 2. 打开 WebSocket 接收流式 chunk
    try {
      const session = await auth();
      const accessToken = session?.accessToken;
      if (!accessToken) {
        setError('请先登录');
        setStatus('error');
        return;
      }

      const wsBase = process.env.NEXT_PUBLIC_WS_BASE_URL ?? 'wss://api.yefzyj.top';
      const url = `${wsBase}/api/v1/ws/llm?token=${encodeURIComponent(accessToken)}&evaluation_id=${evaluationId}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus('streaming');
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as
            | { type: 'chunk'; text: string }
            | { type: 'done'; model: string }
            | { type: 'error'; message: string };

          if (msg.type === 'chunk') {
            setText((prev) => prev + msg.text);
          } else if (msg.type === 'done') {
            setModel(msg.model);
            setStatus('done');
            ws.close();
            router.refresh();
          } else if (msg.type === 'error') {
            setError(msg.message);
            setStatus('error');
            ws.close();
          }
        } catch (err) {
          console.error('WS parse error:', err);
        }
      };

      ws.onerror = () => {
        setError('WebSocket 连接失败');
        setStatus('error');
      };

      ws.onclose = (event) => {
        if (status !== 'done' && event.code !== 1000) {
          // 异常关闭
          if (!error) {
            setError(`连接关闭 (code ${event.code})`);
            setStatus('error');
          }
        }
      };
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.detail);
      } else {
        setError('生成失败,请稍后重试');
      }
      setStatus('error');
    }
  };

  if (initialFeedback) {
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Badge variant="success" className="gap-1">
            <CheckCircle2 className="h-3 w-3" />
            AI 反馈已生成
          </Badge>
          <span>模型 {initialFeedback.model}</span>
          <span>·</span>
          <span>{initialFeedback.latency_ms}ms</span>
          {initialFeedback.simplified_for_senior && (
            <Badge variant="piano" className="text-[10px]">
              银发简化
            </Badge>
          )}
        </div>
        <FeedbackText text={initialFeedback.text} />
        <div className="pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={startGeneration}
            disabled={status === 'streaming' || status === 'connecting'}
          >
            <Sparkles className="mr-1.5 h-3 w-3" />
            重新生成
          </Button>
        </div>
      </div>
    );
  }

  if (status === 'idle') {
    return (
      <div className="rounded-lg border border-dashed border-piano-500/40 bg-piano-500/5 p-6 text-center">
        <Sparkles className="mx-auto h-8 w-8 text-piano-500" />
        <h3 className="mt-2 font-semibold">AI 教练深度反馈</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          用 GPT/Qwen 流式分析你的 5 维评分,给出针对性建议。
          {isSenior && ' (银发模式:已简化专业术语)'}
        </p>
        <Button onClick={startGeneration} variant="piano" className="mt-4">
          <Sparkles className="mr-2 h-4 w-4" />
          生成 AI 反馈
        </Button>
      </div>
    );
  }

  if (status === 'connecting') {
    return (
      <div className="flex items-center justify-center gap-2 rounded-lg border border-dashed p-8 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        正在建立 WebSocket 连接...
      </div>
    );
  }

  if (status === 'error') {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>生成失败</AlertTitle>
        <AlertDescription>
          {error}
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={startGeneration}
          >
            重试
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  // streaming or done
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        {status === 'streaming' ? (
          <>
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>正在生成...</span>
          </>
        ) : (
          <>
            <CheckCircle2 className="h-3 w-3 text-green-500" />
            <span>生成完成</span>
            {model && <span>· {model}</span>}
          </>
        )}
      </div>
      <FeedbackText text={text} streaming={status === 'streaming'} />
    </div>
  );
}

function FeedbackText({ text, streaming = false }: { text: string; streaming?: boolean }) {
  if (!text) {
    return (
      <div className="rounded-md bg-muted/50 p-4 text-sm text-muted-foreground">
        等待 AI 输出...
      </div>
    );
  }
  return (
    <div
      className={`prose prose-sm dark:prose-invert max-w-none rounded-md bg-muted/30 p-4 ${
        streaming ? 'border-l-2 border-piano-500' : ''
      }`}
    >
      {text.split('\n').map((line, i) => (
        <p key={i} className="leading-relaxed">
          {line || '\u00a0'}
        </p>
      ))}
    </div>
  );
}
