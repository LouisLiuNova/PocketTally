// 同源 API 客户端，统一转发 SSR Cookie 与 CSRF Header。

import type { FetchOptions } from 'ofetch'

const unsafeMethods = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

export function useApi() {
  const requestFetch = useRequestFetch()

  return async <T>(request: string, options: FetchOptions<'json'> = {}) => {
    const headers = new Headers(options.headers as HeadersInit | undefined)
    const method = String(options.method || 'GET').toUpperCase()
    if (unsafeMethods.has(method)) headers.set('X-PocketTally-CSRF', '1')
    if (method !== 'GET' && options.body && !headers.has('content-type')) headers.set('content-type', 'application/json')
    try {
      return await requestFetch<T>(request, { ...options, headers } as any)
    } catch (error: any) {
      if (import.meta.client && error?.statusCode === 401 && !request.includes('/auth/')) {
        useAuth().clear()
        const route = useRoute()
        await navigateTo({ path: '/login', query: { redirect: route.fullPath } })
      }
      throw error
    }
  }
}
