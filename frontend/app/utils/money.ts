// HTTP 使用元金额，表单先校验两位小数；统计只累加整数分。
export function minor(value: string | number): number {
  const match = String(value).match(/^(-?)(\d+)(?:\.(\d{1,2}))?$/)
  if (!match) throw new Error('金额最多保留两位小数')
  const result = (Number(match[2]) * 100 + Number((match[3] || '').padEnd(2, '0'))) * (match[1] ? -1 : 1)
  if (!Number.isSafeInteger(result)) throw new Error('金额超出可精确处理范围')
  return result
}
export function money(cents: number): string {
  return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(cents / 100)
}
export function localInput(value = new Date().toISOString()): string {
  // SQLite 响应可能省略 UTC 后缀；不能将它误读为浏览器本地时间。
  const date = new Date(/[zZ]$|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`)
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}
