import { NextResponse } from 'next/server';

/**
 * Health check endpoint — used by Docker HEALTHCHECK and uptime monitors.
 * Returns 200 if the Next.js server is up.
 */
export async function GET() {
  return NextResponse.json({
    status: 'ok',
    service: 'copiano-web',
    version: process.env.npm_package_version ?? '0.1.0',
    timestamp: new Date().toISOString(),
  });
}
