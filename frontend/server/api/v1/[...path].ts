import nodeFetch from 'node-fetch-native/node'
export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const path = getRouterParam(event, 'path') || ''
  // 仅代理固定后端的账本 API，保持浏览器同源；生产构建也使用此路由。
  const target = new URL(`/api/v1/${path}`, config.apiBase)
  target.search = getRequestURL(event).search
  const headers = getProxyRequestHeaders(event)
  // 保留浏览器访问的 Host，供后端执行同源校验。
  const requestHost = getRequestHeader(event, 'host')
  if (requestHost) headers.host = requestHost
  for (const name of ['forwarded', 'x-forwarded-for', 'x-forwarded-host', 'x-forwarded-proto', 'x-real-ip', 'x-pockettally-client-ip']) {
    delete headers[name]
  }
  // Caddy is the only public entrypoint and Nuxt listens on loopback. Caddy
  // replaces incoming X-Forwarded-For, so this is the real client address.
  headers['x-pockettally-client-ip'] = getRequestIP(event, { xForwardedFor: true }) || 'unknown'
  // Node 原生 fetch 会覆盖 Host；使用现有 UnJS HTTP 实现保证转发值不变。
  return proxyRequest(event, target.toString(), { headers, fetch: nodeFetch })
})
