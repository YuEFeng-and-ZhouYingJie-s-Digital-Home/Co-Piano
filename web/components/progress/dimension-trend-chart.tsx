'use client';

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { DIMENSION_META, DIMENSIONS_ORDER } from '@/lib/evaluation-types';
import type { ProgressPoint } from '@/lib/progress-types';

interface DimensionTrendChartProps {
  points: ProgressPoint[];
}

const LINE_COLORS: Record<string, string> = {
  pitch: '#6b2cff',
  expressiveness: '#a855f7',
  hand_pose: '#f59e0b',
  rhythm: '#3b82f6',
  sight_reading: '#10b981',
  overall: '#0f172a',
};

export function DimensionTrendChart({ points }: DimensionTrendChartProps) {
  if (points.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>成长曲线</CardTitle>
          <CardDescription>暂无数据</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  // 简化:只显示 1/N 个点的 label
  const stride = Math.max(1, Math.floor(points.length / 8));

  return (
    <Card>
      <CardHeader>
        <CardTitle>5 维成长曲线</CardTitle>
        <CardDescription>
          每次评估一条数据 · {points.length} 次评估
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[360px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={points}
              margin={{ top: 16, right: 16, left: 0, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11 }}
                interval={Math.max(0, stride - 1)}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fontSize: 11 }}
                label={{
                  value: '分数',
                  angle: -90,
                  position: 'insideLeft',
                  style: { fontSize: 11 },
                }}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: 8,
                  border: '1px solid hsl(var(--border))',
                  fontSize: 12,
                }}
                formatter={(value: number, name: string) => {
                  const dim = DIMENSION_META[name as keyof typeof DIMENSION_META];
                  return [value.toFixed(0), dim?.label ?? name];
                }}
              />
              <Legend
                formatter={(name) => {
                  const dim = DIMENSION_META[name as keyof typeof DIMENSION_META];
                  return (
                    <span className="text-xs">
                      {dim?.emoji} {dim?.label ?? name}
                    </span>
                  );
                }}
              />
              {DIMENSIONS_ORDER.map((dim) => (
                <Line
                  key={dim}
                  type="monotone"
                  dataKey={`scores.${dim}`}
                  stroke={LINE_COLORS[dim]}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                  isAnimationActive={false}
                />
              ))}
              <Line
                type="monotone"
                dataKey="overall"
                stroke={LINE_COLORS.overall}
                strokeWidth={3}
                strokeDasharray="5 3"
                dot={false}
                activeDot={{ r: 5 }}
                isAnimationActive={false}
                name="overall"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
