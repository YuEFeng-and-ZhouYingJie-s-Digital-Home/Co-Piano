import { Sparkles } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { Milestone } from '@/lib/about-data';

interface TimelineProps {
  items: readonly Milestone[];
}

export function Timeline({ items }: TimelineProps) {
  return (
    <ol className="relative space-y-8 border-l border-border pl-6 md:pl-8">
      {items.map((item) => (
        <li key={item.version} className="relative">
          {/* 时间点圆圈 */}
          <span
            className={cn(
              'absolute -left-[33px] md:-left-[41px] top-2 flex h-6 w-6 items-center justify-center rounded-full ring-4 ring-background',
              item.major ? 'bg-piano-500 text-white' : 'bg-muted text-muted-foreground',
            )}
          >
            {item.major ? (
              <Sparkles className="h-3 w-3" />
            ) : (
              <span className="h-2 w-2 rounded-full bg-current" />
            )}
          </span>

          <Card className={cn(item.major && 'border-piano-500/40 shadow-md')}>
            <CardContent className="pt-6">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={item.major ? 'piano' : 'outline'} className="font-mono">
                  {item.version}
                </Badge>
                <span className="text-sm text-muted-foreground">{item.date}</span>
                {item.major && (
                  <Badge variant="success" className="ml-auto">
                    里程碑
                  </Badge>
                )}
              </div>
              <h3 className="mt-3 text-lg font-semibold">{item.title}</h3>
              <ul className="mt-2 space-y-1">
                {item.highlights.map((h) => (
                  <li key={h} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <span className="text-piano-500 mt-0.5">·</span>
                    <span>{h}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </li>
      ))}
    </ol>
  );
}
