import { describe, expect, test } from 'bun:test'
import type { CashFlowBucket } from '../app/types/ledger'
import {
  bucketDateFormat,
  cashFlowChartRows,
  cashFlowScale,
  cashFlowSummary,
  clampSelectedIndex,
  sampleBucketIndexes,
} from '../app/utils/cashFlowTrend'

function bucket(overrides: Partial<CashFlowBucket> = {}): CashFlowBucket {
  return {
    startAt: '2026-09-01T00:00:00+08:00',
    endAt: '2026-09-02T00:00:00+08:00',
    incomeAmountMinor: 1000,
    refundAmountMinor: 200,
    expenseAmountMinor: 500,
    netCashFlowMinor: 700,
    ...overrides,
  }
}

describe('现金流趋势计算', () => {
  test('按 API 桶累计四项金额，并验证净额公式', () => {
    expect(cashFlowSummary([
      bucket(),
      bucket({ incomeAmountMinor: 300, refundAmountMinor: 0, expenseAmountMinor: 100, netCashFlowMinor: 200 }),
    ])).toEqual({
      incomeAmountMinor: 1300,
      refundAmountMinor: 200,
      expenseAmountMinor: 600,
      netCashFlowMinor: 900,
      formulaNetCashFlowMinor: 900,
      formulaMatchesApi: true,
    })
  })

  test('保留 API 净额并能发现不一致', () => {
    expect(cashFlowSummary([bucket({ netCashFlowMinor: 999 })]).formulaMatchesApi).toBe(false)
    expect(cashFlowSummary([bucket({ netCashFlowMinor: 999 })]).netCashFlowMinor).toBe(999)
  })

  test('把支出映射为零线下方，并按正负最大值建立共享比例尺', () => {
    expect(cashFlowChartRows([bucket()])[0]).toMatchObject({ income: 1000, refund: 200, expense: -500, net: 700 })
    expect(cashFlowScale([bucket(), bucket({ incomeAmountMinor: 100, refundAmountMinor: 100, expenseAmountMinor: 2000 })])).toEqual([-2000, 2000])
  })

  test('空、全零、单桶、仅流入、仅流出和混合数据都有稳定比例尺', () => {
    expect(cashFlowScale([])).toEqual([-1, 1])
    expect(cashFlowScale([bucket({ incomeAmountMinor: 0, refundAmountMinor: 0, expenseAmountMinor: 0, netCashFlowMinor: 0 })])).toEqual([-1, 1])
    expect(cashFlowScale([bucket({ incomeAmountMinor: 1200, refundAmountMinor: 300, expenseAmountMinor: 0 })])).toEqual([-1500, 1500])
    expect(cashFlowScale([bucket({ incomeAmountMinor: 0, refundAmountMinor: 0, expenseAmountMinor: 800, netCashFlowMinor: -800 })])).toEqual([-800, 800])
  })

  test('长范围只抽样轴标签但保留首尾', () => {
    expect(sampleBucketIndexes(0, 4)).toEqual([])
    expect(sampleBucketIndexes(3, 4)).toEqual([0, 1, 2])
    expect(sampleBucketIndexes(10, 4)).toEqual([0, 3, 6, 9])
    expect(sampleBucketIndexes(10, 1)).toEqual([0])
  })

  test('选中桶刷新、缩短和清空后安全钳制', () => {
    expect(clampSelectedIndex(3, 5)).toBe(3)
    expect(clampSelectedIndex(8, 3)).toBe(2)
    expect(clampSelectedIndex(-2, 3)).toBe(0)
    expect(clampSelectedIndex(2, 0)).toBe(-1)
  })

  test('日粒度和周/月粒度显示真实桶范围', () => {
    expect(bucketDateFormat('day', '2026-09-01T00:00:00+08:00', '2026-09-02T00:00:00+08:00')).toBe('2026-09-01')
    expect(bucketDateFormat('week', '2026-09-01T00:00:00+08:00', '2026-09-08T00:00:00+08:00')).toBe('2026-09-01 至 2026-09-08')
    expect(bucketDateFormat('month', '2026-09-01T00:00:00+08:00', '2026-10-01T00:00:00+08:00')).toBe('2026-09-01 至 2026-10-01')
  })
})
