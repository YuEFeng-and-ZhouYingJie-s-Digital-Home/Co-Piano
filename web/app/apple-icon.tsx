import { ImageResponse } from 'next/og';

export const runtime = 'edge';
export const size = { width: 180, height: 180 };
export const contentType = 'image/png';

/** Apple touch icon — iOS 主屏幕图标,180x180 */
export default async function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #6b2cff 0%, #3a109a 100%)',
          color: 'white',
          fontSize: 100,
        }}
      >
        🎹
      </div>
    ),
    { ...size },
  );
}
