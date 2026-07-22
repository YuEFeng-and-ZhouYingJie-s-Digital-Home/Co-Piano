'use client';

import { Button } from '@/components/ui/button';
import { RANGE_OPTIONS, type RangeKey } from '@/lib/progress-types';
import { cn } from '@/lib/utils';

interface RangeSelectorProps {
  value: RangeKey;
  onChange: (v: RangeKey) => void;
}

export function RangeSelector({ value, onChange }: RangeSelectorProps) {
  return (
    <div className="inline-flex rounded-md border border-border bg-muted/30 p-1">
      {RANGE_OPTIONS.map((opt) => {
        const active = opt.key === value;
        return (
          <Button
            key={opt.key}
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => onChange(opt.key)}
            className={cn(
              'rounded-sm',
              active && 'bg-background shadow-sm text-foreground',
            )}
          >
            {opt.label}
          </Button>
        );
      })}
    </div>
  );
}
