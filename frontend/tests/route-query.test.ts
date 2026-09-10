import { describe, expect, test } from 'bun:test'
import {
  compactQuery,
  defaultStatisticsState,
  defaultTransactionState,
  parseStatisticsQuery,
  parseTransactionQuery,
  queriesEqual,
  serializeStatisticsState,
  serializeTransactionState,
  statisticsPeriod,
} from '../app/utils/routeQuery'

const today = '2026-09-10'
const uuid = '123e4567-e89b-12d3-a456-426614174000'

describe('交易页 query 契约', () => {
  test('默认值不写入 URL，并能稳定往返', () => {
    const defaults = defaultTransactionState(today)
    expect(compactQuery(serializeTransactionState(defaults, today))).toEqual({})
    const parsed = parseTransactionQuery({}, today)
    expect(parsed.state).toEqual(defaults)
    expect(queriesEqual({}, parsed.query)).toBe(true)
  })

  test('保留有效筛选和显式无边界日期', () => {
    const parsed = parseTransactionQuery({
      q: '  午餐  ', page: '3', start: '', end: '2026-09-20', type: 'expense',
      accountId: uuid, categoryId: uuid, tagId: uuid, status: 'all',
    }, today)
    expect(parsed.state).toMatchObject({ q: '午餐', page: 3, start: '', end: '2026-09-20', type: 'expense', status: 'all' })
    expect(compactQuery(parsed.query)).toEqual({
      q: '午餐', page: '3', start: '', end: '2026-09-20', type: 'expense',
      accountId: uuid, categoryId: uuid, tagId: uuid, status: 'all',
    })
  })

  test('移除未知、重复和非法值，倒置范围整体回退', () => {
    const parsed = parseTransactionQuery({
      unknown: 'value', q: ['a', 'b'], page: '-2', start: '2026-09-20', end: '2026-09-01',
      type: 'unknown', accountId: 'missing', status: 'deleted',
    }, today)
    expect(parsed.state).toEqual(defaultTransactionState(today))
    expect(compactQuery(parsed.query)).toEqual({})
  })

  test('规范化比较忽略字段顺序和 undefined', () => {
    expect(queriesEqual({ status: 'all', page: '2' }, { page: '2', status: 'all', q: undefined })).toBe(true)
    expect(queriesEqual({ page: ['2', '3'] }, { page: '2' })).toBe(false)
  })
})

describe('统计页 query 契约', () => {
  test('默认统计状态不写入 URL', () => {
    const defaults = defaultStatisticsState(today)
    expect(compactQuery(serializeStatisticsState(defaults, today))).toEqual({})
    expect(statisticsPeriod(defaults, today)).toEqual({ startDate: '2026-09-01', endDate: '2026-10-01' })
  })

  test('自定义范围、粒度、月份和父分类可往返', () => {
    const parsed = parseStatisticsQuery({
      preset: 'custom', start: '2026-01-01', end: '2026-04-01', granularity: 'month',
      month: '2026-03', parentCategoryId: uuid,
    }, today)
    expect(parsed.state).toEqual({
      preset: 'custom', start: '2026-01-01', end: '2026-04-01', granularity: 'month',
      month: '2026-03', parentCategoryId: uuid,
    })
    expect(statisticsPeriod(parsed.state, today)).toEqual({ startDate: '2026-01-01', endDate: '2026-04-01' })
  })

  test('非法自定义范围整体回退，非自定义预设移除日期', () => {
    expect(parseStatisticsQuery({ preset: 'custom', start: '2026-04-01', end: '2026-01-01', granularity: 'month' }, today).state)
      .toEqual(defaultStatisticsState(today))
    const lastMonth = parseStatisticsQuery({ preset: 'last_month', start: '2020-01-01', end: '2020-02-01' }, today)
    expect(compactQuery(lastMonth.query)).toEqual({ preset: 'last_month' })
    expect(statisticsPeriod(lastMonth.state, today)).toEqual({ startDate: '2026-08-01', endDate: '2026-09-01' })
  })
})
