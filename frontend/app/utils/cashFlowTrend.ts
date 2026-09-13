import type { CashFlowBucket, Granularity } from '~/types/ledger'

export interface CashFlowSummary {
  incomeAmountMinor: number
  refundAmountMinor: number
  expenseAmountMinor: number
  netCashFlowMinor: number
  formulaNetCashFlowMinor: number
  formulaMatchesApi: boolean
}

export interface CashFlowChartRow extends CashFlowBucket {
  x: number
  income: number
  refund: number
  expense: number
  net: number
}

export function cashFlowSummary(buckets: CashFlowBucket[]): CashFlowSummary {
  const summary = buckets.reduce((result, bucket) => ({
    incomeAmountMinor: result.incomeAmountMinor + bucket.incomeAmountMinor,
    refundAmountMinor: result.refundAmountMinor + bucket.refundAmountMinor,
    expenseAmountMinor: result.expenseAmountMinor + bucket.expenseAmountMinor,
    netCashFlowMinor: result.netCashFlowMinor + bucket.netCashFlowMinor,
  }), {
    incomeAmountMinor: 0,
    refundAmountMinor: 0,
    expenseAmountMinor: 0,
    netCashFlowMinor: 0,
  })
  const formulaNetCashFlowMinor = summary.incomeAmountMinor + summary.refundAmountMinor - summary.expenseAmountMinor
  return {
    ...summary,
    formulaNetCashFlowMinor,
    formulaMatchesApi: formulaNetCashFlowMinor === summary.netCashFlowMinor,
  }
}

export function cashFlowChartRows(buckets: CashFlowBucket[]): CashFlowChartRow[] {
  return buckets.map(bucket => ({
    ...bucket,
    x: new Date(bucket.startAt).getTime(),
    income: bucket.incomeAmountMinor,
    refund: bucket.refundAmountMinor,
    expense: -bucket.expenseAmountMinor,
    net: bucket.netCashFlowMinor,
  }))
}

export function cashFlowScale(buckets: CashFlowBucket[]): [number, number] {
  const maxPositive = Math.max(0, ...buckets.map(bucket => bucket.incomeAmountMinor + bucket.refundAmountMinor))
  const maxNegative = Math.max(0, ...buckets.map(bucket => bucket.expenseAmountMinor))
  const extent = Math.max(1, maxPositive, maxNegative)
  return [-extent, extent]
}

export function clampSelectedIndex(index: number, length: number): number {
  if (!length) return -1
  return Math.min(Math.max(index, 0), length - 1)
}

export function sampleBucketIndexes(length: number, maxLabels: number): number[] {
  if (length <= 0 || maxLabels <= 0) return []
  if (maxLabels === 1) return [0]
  if (length <= maxLabels) return Array.from({ length }, (_, index) => index)
  const last = length - 1
  return Array.from({ length: maxLabels }, (_, index) => Math.round(index * last / (maxLabels - 1)))
}

export function bucketDateFormat(granularity: Granularity, startAt: string, endAt: string): string {
  const start = startAt.slice(0, 10)
  const end = endAt.slice(0, 10)
  if (granularity === 'day') return start
  return `${start} 至 ${end}`
}
