'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { Check, X, Loader2, ChevronRight } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { api, ApiError } from '@/lib/api';
import {
  LEVEL_META,
  MODE_META,
  midiToNoteName,
  midiToSolfege,
  type SightReadingSession,
  type SightReadingQuestion,
} from '@/lib/sight-reading-types';
import { cn } from '@/lib/utils';

interface QuestionRunnerProps {
  session: SightReadingSession;
}

export function QuestionRunner({ session }: QuestionRunnerProps) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [selected, setSelected] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<
    | { correct: boolean; correctMidi: number; timeMs: number }
    | null
  >(null);
  const [error, setError] = useState<string | null>(null);
  const startTimeRef = useState<number>(Date.now())[0];

  if (session.finished) {
    return <SessionSummary session={session} onRestart={() => router.push('/app/sight-reading')} />;
  }

  const currentQ = session.questions[session.current_index];
  if (!currentQ) return null;

  const totalQuestions = session.questions.length;
  const progressPct =
    ((session.current_index + (feedback ? 1 : 0)) / totalQuestions) * 100;

  const onAnswer = (midi: number) => {
    if (selected !== null || pending) return;
    setSelected(midi);
    const timeMs = Date.now() - startTimeRef;

    startTransition(async () => {
      try {
        const result = await api.post<{ correct: boolean; correct_midi: number }>(
          `/api/v1/sight-reading/${session.id}/answer`,
          {
            question_id: currentQ.id,
            selected_midi: midi,
            time_taken_ms: timeMs,
          },
        );
        setFeedback({
          correct: result.correct,
          correctMidi: result.correct_midi,
          timeMs,
        });
      } catch (e) {
        setError(e instanceof ApiError ? e.detail : '提交失败');
        setSelected(null);
      }
    });
  };

  const next = async () => {
    setSelected(null);
    setFeedback(null);
    setError(null);
    try {
      // 拉最新 session 状态(后端可能会更新 finished)
      const updated = await api.get<SightReadingSession>(
        `/api/v1/sight-reading/${session.id}`,
      );
      if (updated.finished) {
        router.refresh();
      } else {
        router.refresh(); // RSC 重新拉
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : '加载下一题失败');
    }
  };

  return (
    <div className="space-y-4 max-w-3xl mx-auto">
      {/* 顶部 meta + 进度 */}
      <div>
        <div className="flex items-center justify-between text-sm text-muted-foreground mb-2 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Badge variant="piano">L{session.level} {LEVEL_META[session.level].label}</Badge>
            <Badge variant="outline">{MODE_META[session.mode].label}</Badge>
            <span>
              题 {session.current_index + 1} / {totalQuestions}
            </span>
          </div>
          <span className="text-piano-500 font-medium tabular-nums">
            正确 {session.correct_count}
          </span>
        </div>
        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-piano-500 to-piano-300 transition-all"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* 题目卡 */}
      <Card>
        <CardContent className="pt-6">
          <div className="text-center space-y-4">
            <p className="text-sm text-muted-foreground">
              {currentQ.prompt ?? '看谱,选正确的音'}
            </p>
            <QuestionDisplay question={currentQ} mode={session.mode} />
          </div>

          {/* 选项 */}
          <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-3">
            {currentQ.options.map((midi) => {
              const isSelected = selected === midi;
              const isCorrect = feedback?.correctMidi === midi;
              const isWrong =
                feedback && isSelected && !feedback.correct;
              return (
                <button
                  key={midi}
                  type="button"
                  onClick={() => onAnswer(midi)}
                  disabled={selected !== null || pending}
                  className={cn(
                    'rounded-lg border-2 p-4 text-center font-mono font-bold transition-all',
                    'hover:border-piano-500 disabled:cursor-not-allowed',
                    isCorrect && 'border-green-500 bg-green-500/10 text-green-700',
                    isWrong && 'border-red-500 bg-red-500/10 text-red-700',
                    isSelected && !feedback && 'border-piano-500 bg-piano-500/10',
                    !isSelected && !isCorrect && !isWrong && 'border-border',
                  )}
                >
                  <div className="text-2xl">{midiToNoteName(midi)}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    {midiToSolfege(midi)}
                  </div>
                </button>
              );
            })}
          </div>

          {/* 反馈区 */}
          {feedback && (
            <div
              className={cn(
                'mt-4 rounded-md px-4 py-3 flex items-center justify-between',
                feedback.correct
                  ? 'bg-green-500/10 text-green-700 dark:text-green-300'
                  : 'bg-red-500/10 text-red-700 dark:text-red-300',
              )}
            >
              <div className="flex items-center gap-2 text-sm">
                {feedback.correct ? (
                  <>
                    <Check className="h-4 w-4" />
                    <span>正确!{(feedback.timeMs / 1000).toFixed(1)}s</span>
                  </>
                ) : (
                  <>
                    <X className="h-4 w-4" />
                    <span>
                      正确答案是{' '}
                      <strong>{midiToNoteName(feedback.correctMidi)}</strong>
                    </span>
                  </>
                )}
              </div>
              <Button onClick={next} size="sm" variant="piano">
                {session.current_index + 1 >= totalQuestions
                  ? '查看结果'
                  : '下一题'}
                <ChevronRight className="ml-1 h-3 w-3" />
              </Button>
            </div>
          )}

          {error && (
            <div className="mt-3 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}
          {pending && (
            <div className="mt-3 flex items-center justify-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin" />
              提交中...
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function QuestionDisplay({
  question,
  mode,
}: {
  question: SightReadingQuestion;
  mode: SightReadingSession['mode'];
}) {
  if (mode === 'staff') {
    return (
      <div className="text-2xl font-mono">
        {question.notes_midi.map((m, i) => (
          <span key={i} className="mx-1">
            {midiToNoteName(m)}
          </span>
        ))}
        <div className="mt-2 text-xs text-muted-foreground">
          (五线谱 VexFlow 渲染待 W7 集成)
        </div>
      </div>
    );
  }
  if (mode === 'numbered') {
    return (
      <div className="text-3xl font-bold">
        {question.notes_solfege.map((s, i) => (
          <span key={i} className="mx-1">
            {s}
          </span>
        ))}
      </div>
    );
  }
  // dual
  return (
    <div>
      <div className="text-2xl font-mono">
        {question.notes_midi.map((m, i) => (
          <span key={i} className="mx-1">
            {midiToNoteName(m)}
          </span>
        ))}
      </div>
      <div className="mt-2 text-2xl font-bold">
        {question.notes_solfege.map((s, i) => (
          <span key={i} className="mx-1">
            {s}
          </span>
        ))}
      </div>
    </div>
  );
}

function SessionSummary({
  session,
  onRestart,
}: {
  session: SightReadingSession;
  onRestart: () => void;
}) {
  const accuracy = (session.correct_count / session.questions.length) * 100;
  const passed = accuracy >= 80;
  return (
    <Card className={passed ? 'border-green-500/40' : 'border-amber-500/40'}>
      <CardContent className="pt-6 text-center space-y-4">
        <div className="text-6xl">{passed ? '🎉' : '💪'}</div>
        <h2 className="text-2xl font-bold">
          {passed ? '太棒了!' : '继续努力'}
        </h2>
        <div className="text-5xl font-bold text-piano-500 tabular-nums">
          {Math.round(accuracy)}%
        </div>
        <p className="text-sm text-muted-foreground">
          {session.correct_count} / {session.questions.length} 正确
        </p>
        <div className="flex gap-2 justify-center">
          <Button onClick={onRestart} variant="piano">
            再来一轮
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
