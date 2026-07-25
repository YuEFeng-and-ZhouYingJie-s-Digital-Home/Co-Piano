/**
 * CoPiano API Client — 类型安全 fetch wrapper
 * 自动注入 JWT (从 NextAuth session 拿) + 错误处理
 */

import { auth } from '@/auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'https://api.yefzyj.top';

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public payload?: unknown,
  ) {
    super(`[${status}] ${detail}`);
    this.name = 'ApiError';
  }
}

export interface ApiOptions extends Omit<RequestInit, 'body'> {
  /** 请求体(自动 JSON.stringify) */
  body?: unknown;
  /** 是否跳过鉴权(用于 /auth/login 等) */
  skipAuth?: boolean;
  /** 超时(ms),默认 30s */
  timeoutMs?: number;
}

/**
 * 通用 fetch wrapper
 * - 自动注入 Authorization (来自 NextAuth session.accessToken)
 * - 统一处理 4xx/5xx 抛 ApiError
 * - 支持 FormData(multipart 上传 MIDI)
 */
export async function apiFetch<T = unknown>(
  path: string,
  options: ApiOptions = {},
): Promise<T> {
  const {
    body,
    skipAuth = false,
    timeoutMs = 30_000,
    headers: userHeaders,
    ...rest
  } = options;

  // 鉴权
  const headers = new Headers(userHeaders);
  if (!skipAuth) {
    const session = await auth();
    if (session?.accessToken) {
      headers.set('Authorization', `Bearer ${session.accessToken}`);
    }
  }

  // body 处理
  let bodyValue: BodyInit | undefined;
  if (body !== undefined) {
    if (body instanceof FormData) {
      bodyValue = body;
      // 不要手动设 Content-Type,让浏览器加 boundary
    } else {
      bodyValue = JSON.stringify(body);
      headers.set('Content-Type', 'application/json');
    }
  }

  // 超时
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      headers,
      body: bodyValue,
      signal: controller.signal,
    });

    if (!res.ok) {
      let detail = res.statusText;
      let payload: unknown;
      try {
        payload = await res.json();
        if (typeof payload === 'object' && payload !== null && 'detail' in payload) {
          detail = String((payload as { detail: unknown }).detail);
        }
      } catch {
        // 不是 JSON
      }
      throw new ApiError(res.status, detail, payload);
    }

    // 204 No Content
    if (res.status === 204) return undefined as T;

    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

/** 便捷方法 */
export const api = {
  get: <T>(path: string, options?: Omit<ApiOptions, 'body'>) =>
    apiFetch<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: Omit<ApiOptions, 'body'>) =>
    apiFetch<T>(path, { ...options, method: 'POST', body }),
  put: <T>(path: string, body?: unknown, options?: Omit<ApiOptions, 'body'>) =>
    apiFetch<T>(path, { ...options, method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown, options?: Omit<ApiOptions, 'body'>) =>
    apiFetch<T>(path, { ...options, method: 'PATCH', body }),
  delete: <T>(path: string, options?: Omit<ApiOptions, 'body'>) =>
    apiFetch<T>(path, { ...options, method: 'DELETE' }),
  upload: <T>(path: string, formData: FormData, options?: Omit<ApiOptions, 'body'>) =>
    apiFetch<T>(path, { ...options, method: 'POST', body: formData, timeoutMs: 120_000 }),
};
