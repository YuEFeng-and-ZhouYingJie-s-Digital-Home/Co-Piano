import { Music, Hand, Eye, Type, Brain } from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const DIMENSIONS = [
  {
    icon: Music,
    name: '音准 (Pitch)',
    weight: '20%',
    color: 'text-piano-500',
    bg: 'bg-piano-500/10',
    desc: '对比参考 MIDI,精确到 1 音分,识别走音/错音/漏音。',
    detail: '基于 AMT (Automatic Music Transcription) 算法,适配古典钢琴 88 键全音域。',
  },
  {
    icon: Brain,
    name: '表现力 (Expressiveness)',
    weight: '25%',
    color: 'text-purple-500',
    bg: 'bg-purple-500/10',
    desc: '9 维向量:力度/节奏/踏板/连断/装饰音/速度/呼吸/动态/句法。',
    detail: '业界首个多维表现力评估,超越传统 1 维 "对错" 评判。',
  },
  {
    icon: Hand,
    name: '手型 (Hand Pose)',
    weight: '20%',
    color: 'text-amber-500',
    bg: 'bg-amber-500/10',
    desc: '9 个关键关节点:腕/指/掌/肘/肩,预防腱鞘炎等劳损。',
    detail: '基于 MediaPipe Hands 关键点检测,业界首个手型评估。',
  },
  {
    icon: Music,
    name: '节奏 (Rhythm)',
    weight: '20%',
    color: 'text-blue-500',
    bg: 'bg-blue-500/10',
    desc: '节拍偏差、速度稳定性、自由速度的合理性。',
    detail: '5 维节律特征,符合钢琴教学法 (Suzuki/Beyer/Kodály)。',
  },
  {
    icon: Eye,
    name: '视奏 (Sight Reading)',
    weight: '15%',
    color: 'text-green-500',
    bg: 'bg-green-500/10',
    desc: '4 难度 × 3 模式 × 3 输入 (五线谱/简谱/双行) 训练。',
    detail: '从单音 → 简单旋律 → 复调,逐步挑战。',
  },
] as const;

export function FiveDimensions() {
  return (
    <section
      id="five-dimensions"
      className="border-b border-border/40 bg-muted/30 py-20 md:py-28"
    >
      <div className="container">
        <div className="mx-auto max-w-2xl text-center">
          <Badge variant="piano" className="mb-4">业界首个</Badge>
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl">
            5 维 AI 评估
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            超越传统 1 维 "对错" 评判,看每一个细节。
          </p>
        </div>

        <div className="mt-16 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {DIMENSIONS.map((dim) => {
            const Icon = dim.icon;
            return (
              <Card
                key={dim.name}
                className="group relative overflow-hidden transition-all hover:shadow-lg hover:-translate-y-1"
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div
                      className={`flex h-12 w-12 items-center justify-center rounded-lg ${dim.bg}`}
                    >
                      <Icon className={`h-6 w-6 ${dim.color}`} />
                    </div>
                    <Badge variant="outline" className="font-mono">
                      权重 {dim.weight}
                    </Badge>
                  </div>
                  <CardTitle className="mt-4 text-xl">{dim.name}</CardTitle>
                  <CardDescription className="text-base leading-relaxed">
                    {dim.desc}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {dim.detail}
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
