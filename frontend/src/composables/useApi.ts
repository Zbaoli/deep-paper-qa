const BASE = '/api'

/**
 * 通用 REST 请求封装
 * @param path - 相对于 /api 的路径
 * @param options - fetch 选项
 */
export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) {
    throw new Error(`API error: ${resp.status} ${resp.statusText}`)
  }
  return resp.json()
}

/**
 * POST 请求封装
 * @param path - 相对于 /api 的路径
 * @param body - 请求体（自动序列化为 JSON）
 */
export async function postApi<T>(path: string, body: unknown): Promise<T> {
  return fetchApi<T>(path, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
