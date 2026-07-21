import { Users, BookOpen, Clock, Award } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

const STATS = [
  {
    icon: Users,
    value: '60',
    unit: '名学生',
    label: 'RCT 真实数据',
  },
  {
    icon: BookOpen,
    value: '5',
    unit: '维评估',
    label: '业界首个多维评估',
  },
  {
    icon: Clock,
    value: '7',
    unit: '天',
    label: '自适应课程周期',
  },
  {
    icon: Award,
    value: '1.34',
    unit: "Cohen's d",
    label: '效应量 (超 ITS Meta 3.3×)',
  },
] as const;

export function Stats() {
  return (
    <section className="border-b border-border/40 py-16 md:py-20">
      <div className="container">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STATS.map((stat) => {
            const Icon = stat.icon;
            return (
              <Card
                key={stat.label}
                className="text-center transition-all hover:shadow-md"
              >
                <CardContent className="pt-6">
                  <Icon className="mx-auto h-8 w-8 text-piano-500" />
                  <div className="mt-3 flex items-baseline justify-center gap-1">
                    <span className="text-4xl font-bold tracking-tight">
                      {stat.value}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      {stat.unit}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {stat.label}
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
}
