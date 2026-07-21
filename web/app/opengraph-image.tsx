import { ImageResponse } from 'next/og';

export const runtime = 'edge';
export const alt = 'CoPiano — AI 古典钢琴教练';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

/**
 * 动态 OG image — 部署时由 Vercel/Edge runtime 生成
 * 默认首页分享时显示
 */
export default async function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #6b2cff 0%, #3a109a 100%)',
          color: 'white',
          padding: 80,
          fontFamily: 'sans-serif',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 16,
            fontSize: 80,
            fontWeight: 'bold',
          }}
        >
          <span>🎹</span>
          <span>CoPiano</span>
        </div>
        <div
          style={{
            marginTop: 32,
            fontSize: 36,
            textAlign: 'center',
            opacity: 0.95,
          }}
        >
          AI 古典钢琴教练
        </div>
        <div
          style={{
            marginTop: 24,
            fontSize: 28,
            textAlign: 'center',
            opacity: 0.85,
            maxWidth: 900,
          }}
        >
          5 维评估 + RCT 验证 d=1.34
        </div>
        <div
          style={{
            marginTop: 80,
            display: 'flex',
            gap: 32,
            fontSize: 22,
            opacity: 0.8,
          }}
        >
          <span>✓ 5 维 AI 评估</span>
          <span>✓ 7 天自适应课程</span>
          <span>✓ 银发长者免费</span>
        </div>
      </div>
    ),
    { ...size },
  );
}
