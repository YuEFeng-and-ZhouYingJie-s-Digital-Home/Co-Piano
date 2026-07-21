import Link from 'next/link';
import { CheckCircle2, Circle, Clock } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import {
  BLOCK_META,
  DIMENSION_META,
  type CurriculumDay,
  type CurriculumWeek,
} from '@/lib/curriculum-types';

interface CurriculumWeekViewProps {
  week: CurriculumWeek;
}

export function CurriculumWeekView({ week }: CurriculumWeekViewProps) {
  return (
    <div>
      {/* 总览条 */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <Stat label="当前进度" value={`Day ${week.current_day}/7`} />
            <Stat
              label="完成度"
              value={`${Math.round(week.completion_ratio * 100)}%`}
            />
            <Stat
              label="已完成块"
              value={`${week.stats.blocks_done}/${week.stats.blocks_total}`}
            />
            <Stat
              label="已练习"
              value={`${week.stats.minutes_done}/${week.stats.minutes_total} 分钟`}
            />
          </div>
          {/* 进度条 */}
          <div className="mt-4 h-2 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-piano-500 to-piano-300 transition-all"
              style={{ width: `${week.completion_ratio * 100}%` }}
            />
          </div>
        </CardContent>
      </Card>

      {/* 7 天网格 */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {week.days.map((day) => (
          <DayCard key={day.day_num} day={day} isToday={day.day_num === week.current_day} />
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-0.5 text-lg font-semibold">{value}</div>
    </div>
  );
}

function DayCard({ day, isToday }: { day: CurriculumDay; isToday: boolean }) {
  const focusEmoji = day.focus_dimension
    ? DIMENSION_META[day.focus_dimension]?.emoji
    : null;

  return (
    <Link href={`/app/curriculum/${day.day_num}`}>
      <Card
        className={cn(
          'h-full transition-all hover:shadow-md hover:-translate-y-0.5 cursor-pointer',
          isToday && 'border-piano-500 ring-2 ring-piano-500/20',
        )}
      >
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="text-xs text-muted-foreground">
                {new Date(day.date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })}
              </div>
              <div className="mt-0.5 text-lg font-bold flex items-center gap-2">
                Day {day.day_num}
                {isToday && <Badge variant="piano" className="text-[10px] py-0">今天</Badge>}
              </div>
            </div>
            {day.completed ? (
              <CheckCircle2 className="h-6 w-6 text-green-500" />
            ) : (
              <Circle className="h-6 w-6 text-muted-foreground/30" />
            )}
          </div>

          <h3 className="font-semibold text-sm line-clamp-2 min-h-[2.5rem]">
            {day.title}
          </h3>

          {focusEmoji && (
            <div className="mt-2 text-xs text-muted-foreground">
              重点: {focusEmoji} {day.focus_dimension && DIMENSION_META[day.focus_dimension]?.label}
            </div>
          )}

          <div className="mt-3 flex items-center justify-between text-xs">
            <div className="flex items-center gap-1 text-muted-foreground">
              <Clock className="h-3 w-3" />
              {day.total_min} 分钟
            </div>
            <div className="text-muted-foreground">
              {day.blocks.filter((b) => b.completed).length}/{day.blocks.length} 块
            </div>
          </div>

          {/* Block 预览 */}
          <div className="mt-3 flex flex-wrap gap-1">
            {day.blocks.slice(0, 4).map((block) => {
              const meta = BLOCK_META[block.block_type];
              return (
                <span
                  key={block.id}
                  className={cn(
                    'text-base',
                    block.completed ? 'opacity-100' : 'opacity-50',
                  )}
                  title={meta?.label ?? block.block_type}
                >
                  {meta?.emoji ?? '•'}
                </span>
              );
            })}
            {day.blocks.length > 4 && (
              <span className="text-xs text-muted-foreground">
                +{day.blocks.length - 4}
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
