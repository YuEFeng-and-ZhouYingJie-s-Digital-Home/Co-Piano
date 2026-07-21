'use client';

import { useState } from 'react';
import Link from 'next/link';
import { CheckCircle2, Circle, Clock, Music, ExternalLink, Play } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { CompleteBlockButton } from '@/components/curriculum/complete-block-button';
import { BLOCK_META, type CurriculumBlock, type BlockType } from '@/lib/curriculum-types';
import { cn } from '@/lib/utils';

interface BlockCardProps {
  block: CurriculumBlock;
}

export function BlockCard({ block }: BlockCardProps) {
  const meta = BLOCK_META[block.block_type as BlockType];
  const [expanded, setExpanded] = useState(false);

  return (
    <Card
      className={cn(
        'transition-all',
        block.completed && 'bg-muted/30 border-green-500/30',
      )}
    >
      <CardContent className="pt-6">
        <div className="flex items-start gap-4">
          {/* Icon + completion */}
          <div className="flex-shrink-0">
            {block.completed ? (
              <CheckCircle2 className="h-7 w-7 text-green-500" />
            ) : (
              <Circle className="h-7 w-7 text-muted-foreground/40" />
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2 flex-wrap">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{meta?.emoji ?? '🎼'}</span>
                  <Badge variant="outline" className={cn('text-xs', meta?.color)}>
                    {meta?.label ?? block.block_type}
                  </Badge>
                </div>
                <h3 className="mt-1.5 font-semibold leading-snug">
                  {block.title}
                </h3>
              </div>
              <CompleteBlockButton
                blockId={block.id}
                completed={block.completed}
                score={block.score}
              />
            </div>

            {block.description && (
              <p
                className={cn(
                  'mt-2 text-sm text-muted-foreground',
                  !expanded && 'line-clamp-2',
                )}
              >
                {block.description}
              </p>
            )}
            {block.description && block.description.length > 100 && (
              <button
                type="button"
                onClick={() => setExpanded((v) => !v)}
                className="mt-1 text-xs text-piano-500 hover:underline"
              >
                {expanded ? '收起' : '展开'}
              </button>
            )}

            {/* 底部 meta */}
            <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {block.duration_min} 分钟
              </div>
              {block.piece_id && (
                <div className="flex items-center gap-1">
                  <Music className="h-3 w-3" />
                  <code className="rounded bg-muted px-1">{block.piece_id}</code>
                </div>
              )}
              {block.score !== undefined && (
                <div className="flex items-center gap-1">
                  <span className="text-green-600 font-medium">得分 {block.score}</span>
                </div>
              )}
            </div>

            {/* Action: 跳转录音 / 视奏 */}
            {(block.block_type === 'main_piece' ||
              block.block_type === 'review_piece' ||
              block.block_type === 'expressiveness' ||
              block.block_type === 'weakness_drill') && (
              <div className="mt-3">
                <Button asChild variant="outline" size="sm">
                  <Link href={`/app/record?block=${block.id}`}>
                    <Play className="mr-1.5 h-3 w-3" />
                    开始录音评估
                  </Link>
                </Button>
              </div>
            )}
            {block.block_type === 'sight_reading' && (
              <div className="mt-3">
                <Button asChild variant="outline" size="sm">
                  <Link href={`/app/sight-reading`}>
                    <ExternalLink className="mr-1.5 h-3 w-3" />
                    进入视奏
                  </Link>
                </Button>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
