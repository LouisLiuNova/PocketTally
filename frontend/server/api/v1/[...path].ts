export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const path = getRouterParam(event, 'path') || ''
  // 仅代理固定后端的账本 API，保持浏览器同源；生产构建也使用此路由。
  const target = new URL(`/api/v1/${path}`, config.apiBase)
  target.search = getRequestURL(event).search
  const headers = getProxyRequestHeaders(event)
  // Keep the browser-facing host for local same-origin validation. The target
  // URL points at the backend, so proxyRequest otherwise replaces Host with
  // 127.0.0.1:8000 and the backend rejects Origin http://127.0.0.1:3000.
  const requestHost = getRequestHeader(event, 'host')
  if (requestHost) headers.host = requestHost
  for (const name of ['forwarded', 'x-forwarded-for', 'x-forwarded-host', 'x-forwarded-proto', 'x-real-ip', 'x-pockettally-client-ip']) {
    delete headers[name]
  }
  // Caddy is the only public entrypoint and Nuxt listens on loopback. Caddy
  // replaces incoming X-Forwarded-For, so this is the real client address.
  headers['x-pockettally-client-ip'] = getRequestIP(event, { xForwardedFor: true }) || 'unknown'
  return proxyRequest(event, target.toString(), { headers })
})
