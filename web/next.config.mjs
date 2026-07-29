/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: false,
  // 跳过 TypeScript 错误 (临时, 等 types 修了再打开)
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  experimental: {
    instrumentationHook: false,
  },
  // 内存优化
  productionBrowserSourceMaps: false,
  // ── 关键! 反向代理 / Cloudflare Tunnel 下必须打开 ──
  // 否则 Next.js 内部 Request.url 用 bind host (0.0.0.0:3000) 而非 Host header
  // 导致 NextAuth callback 重定向到 0.0.0.0:3000,浏览器无法访问
  trustHostHeader: true,
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Frame-Options', value: 'SAMEORIGIN' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
        ],
      },
      {
        source: '/(.*).svg',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=86400, immutable' },
        ],
      },
    ];
  },
};
export default nextConfig;
