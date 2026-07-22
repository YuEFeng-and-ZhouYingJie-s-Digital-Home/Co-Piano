import type { Metadata } from 'next';
import { MidiRecorder } from '@/components/record/midi-recorder';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

export const metadata: Metadata = {
  title: '录音评估',
  description: '5 维 AI 评估,Web MIDI 即插即用',
};

export default function RecordPage() {
  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">录音评估</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          连接 MIDI 键盘,弹奏一段曲子,AI 立刻给出 5 维评分。
        </p>
      </div>

      <MidiRecorder />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">使用提示</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-1.5 text-sm text-muted-foreground list-disc pl-5">
            <li>支持 Chrome / Edge / Opera 桌面版(其他浏览器需 HTTPS 才能用 Web MIDI)</li>
            <li>推荐用 USB MIDI 键盘(Yamaha / Casio / Roland 等)</li>
            <li>没有 MIDI 键盘?出错时可以选择"上传 MIDI 文件"备选方案</li>
            <li>每次评估约 5-30 秒,取决于录音长度</li>
            <li>Free 用户每天 3 次评估,Pro 无限</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
