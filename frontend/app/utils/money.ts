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
  // 账本界面固定显示上海时间，不能跟随浏览器所在时区漂移。
  const date = new Date(/[zZ]$|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`)
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(date)
  const valueOf = (type: string) => parts.find(part => part.type === type)?.value || ''
  return `${valueOf('year')}-${valueOf('month')}-${valueOf('day')}T${valueOf('hour')}:${valueOf('minute')}`
}

export function shanghaiIso(value: string): string {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) throw new Error('请选择有效的发生时间')
  const date = new Date(`${value}:00+08:00`)
  if (Number.isNaN(date.getTime())) throw new Error('请选择有效的发生时间')
  return date.toISOString()
}
