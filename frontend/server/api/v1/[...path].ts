export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const path = getRouterParam(event, 'path') || ''
  // 仅代理固定后端的账本 API，保持浏览器同源；生产构建也使用此路由。
  const target = new URL(`/api/v1/${path}`, config.apiBase)
  target.search = getRequestURL(event).search
  const headers = getProxyRequestHeaders(event)
  for (const name of ['forwarded', 'x-forwarded-for', 'x-forwarded-host', 'x-forwarded-proto', 'x-real-ip', 'x-pockettally-client-ip']) {
    delete headers[name]
  }
  headers['x-pockettally-client-ip'] = getRequestIP(event) || 'unknown'
  return proxyRequest(event, target.toString(), { headers })
})
