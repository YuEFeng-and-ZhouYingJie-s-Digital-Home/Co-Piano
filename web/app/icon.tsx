import { ImageResponse } from 'next/og';

export const runtime = 'edge';
export const size = { width: 64, height: 64 };
export const contentType = 'image/png';

/** 动态 icon — 32x32 浏览器 favicon,会被 Next.js 自动生成多尺寸 */
export default async function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#6b2cff',
          borderRadius: 12,
          color: 'white',
          fontSize: 36,
          fontWeight: 'bold',
        }}
      >
        🎹
      </div>
    ),
    { ...size },
  );
}
