import { ImageResponse } from 'next/og';

export const runtime = 'edge';
export const alt = 'CoPiano — AI 古典钢琴教练';
export const size = { width: 1200, height: 675 };
export const contentType = 'image/png';

/** Twitter Card 大图版 — 16:9 比例 */
export default async function TwitterImage() {
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
          padding: 60,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontSize: 72, fontWeight: 'bold' }}>
          <span>🎹</span>
          <span>CoPiano</span>
        </div>
        <div style={{ marginTop: 24, fontSize: 32, opacity: 0.9 }}>
          AI 古典钢琴教练 · d=1.34
        </div>
      </div>
    ),
    { ...size },
  );
}
