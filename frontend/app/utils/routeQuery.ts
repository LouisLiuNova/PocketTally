import type { Granularity, Kind } from '~/types/ledger'

export type QueryRecord = Record<string, string | undefined>
type QueryInput = Record<string, unknown>

export type TransactionStatus = 'active' | 'voided' | 'all'
export type StatisticsPreset = 'this_month' | 'last_month' | 'year' | 'twelve_months' | 'custom'

export interface TransactionRouteState {
  q: string
  page: number
  start: string
  end: string
  type: Kind | ''
  accountId: string
  categoryId: string
  tagId: string
  status: TransactionStatus
}

export interface StatisticsRouteState {
  preset: StatisticsPreset
  start: string
  end: string
  granularity: Granularity
  month: string
  parentCategoryId: string
}

const KINDS = new Set<Kind>(['income', 'expense', 'transfer', 'balance_adjustment', 'expense_refund'])
const STATUSES = new Set<TransactionStatus>(['active', 'voided', 'all'])
const PRESETS = new Set<StatisticsPreset>(['this_month', 'last_month', 'year', 'twelve_months', 'custom'])
const GRANULARITIES = new Set<Granularity>(['day', 'week', 'month'])
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function scalar(value: unknown): string | undefined {
  return typeof value === 'string' ? value : undefined
}

export function isDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
  const [year = 0, month = 0, day = 0] = value.split('-').map(Number)
  const date = new Date(Date.UTC(year, month - 1, day))
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day
}

export function isMonth(value: string): boolean {
  if (!/^\d{4}-\d{2}$/.test(value)) return false
  const month = Number(value.slice(5))
  return month >= 1 && month <= 12
}

export function shiftMonth(dateValue: string, delta: number): string {
  const [year = 0, month = 0] = dateValue.slice(0, 7).split('-').map(Number)
  const value = new Date(Date.UTC(year, month - 1 + delta, 1))
  return `${value.getUTCFullYear()}-${String(value.getUTCMonth() + 1).padStart(2, '0')}-01`
}

export function nextDate(dateValue: string): string {
  const [year = 0, month = 0, day = 0] = dateValue.split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, day + 1)).toISOString().slice(0, 10)
}

export function monthPeriod(today: string) {
  const start = `${today.slice(0, 7)}-01`
  return { start, end: shiftMonth(start, 1) }
}

export function statisticsPeriod(state: StatisticsRouteState, today: string) {
  const current = monthPeriod(today)
  if (state.preset === 'last_month') return { startDate: shiftMonth(current.start, -1), endDate: current.start }
  if (state.preset === 'year') return { startDate: `${today.slice(0, 4)}-01-01`, endDate: `${Number(today.slice(0, 4)) + 1}-01-01` }
  if (state.preset === 'twelve_months') return { startDate: shiftMonth(current.start, -11), endDate: current.end }
  if (state.preset === 'custom') return { startDate: state.start, endDate: state.end }
  return { startDate: current.start, endDate: current.end }
}

export function defaultTransactionState(today: string): TransactionRouteState {
  const period = monthPeriod(today)
  return { q: '', page: 1, start: period.start, end: period.end, type: '', accountId: '', categoryId: '', tagId: '', status: 'active' }
}

export function serializeTransactionState(state: TransactionRouteState, today: string): QueryRecord {
  const defaults = defaultTransactionState(today)
  return {
    q: state.q || undefined,
    page: state.page === 1 ? undefined : String(state.page),
    start: state.start === defaults.start ? undefined : state.start,
    end: state.end === defaults.end ? undefined : state.end,
    type: state.type || undefined,
    accountId: state.accountId || undefined,
    categoryId: state.categoryId || undefined,
    tagId: state.tagId || undefined,
    status: state.status === 'active' ? undefined : state.status,
  }
}

export function parseTransactionQuery(query: QueryInput, today: string) {
  const state = defaultTransactionState(today)
  const q = scalar(query.q)
  const page = scalar(query.page)
  const start = scalar(query.start)
  const end = scalar(query.end)
  const type = scalar(query.type)
  const status = scalar(query.status)
  state.q = q?.trim() || ''
  if (page && /^\d+$/.test(page) && Number(page) > 0) state.page = Number(page)
  if (start === '' || (start && isDate(start))) state.start = start
  if (end === '' || (end && isDate(end))) state.end = end
  if (state.start && state.end && state.start >= state.end) {
    const defaults = defaultTransactionState(today)
    state.start = defaults.start
    state.end = defaults.end
  }
  if (type && KINDS.has(type as Kind)) state.type = type as Kind
  if (status && STATUSES.has(status as TransactionStatus)) state.status = status as TransactionStatus
  for (const key of ['accountId', 'categoryId', 'tagId'] as const) {
    const value = scalar(query[key])
    if (value && UUID_PATTERN.test(value)) state[key] = value
  }
  return { state, query: serializeTransactionState(state, today) }
}

export function defaultStatisticsState(today: string): StatisticsRouteState {
  const period = monthPeriod(today)
  return { preset: 'this_month', start: period.start, end: period.end, granularity: 'day', month: today.slice(0, 7), parentCategoryId: '' }
}

export function serializeStatisticsState(state: StatisticsRouteState, today: string): QueryRecord {
  return {
    preset: state.preset === 'this_month' ? undefined : state.preset,
    start: state.preset === 'custom' ? state.start : undefined,
    end: state.preset === 'custom' ? state.end : undefined,
    granularity: state.granularity === 'day' ? undefined : state.granularity,
    month: state.month === today.slice(0, 7) ? undefined : state.month,
    parentCategoryId: state.parentCategoryId || undefined,
  }
}

export function parseStatisticsQuery(query: QueryInput, today: string) {
  const state = defaultStatisticsState(today)
  const preset = scalar(query.preset)
  const granularity = scalar(query.granularity)
  const month = scalar(query.month)
  const parentCategoryId = scalar(query.parentCategoryId)
  if (preset && PRESETS.has(preset as StatisticsPreset)) state.preset = preset as StatisticsPreset
  if (granularity && GRANULARITIES.has(granularity as Granularity)) state.granularity = granularity as Granularity
  if (month && isMonth(month)) state.month = month
  if (parentCategoryId && UUID_PATTERN.test(parentCategoryId)) state.parentCategoryId = parentCategoryId
  if (state.preset === 'custom') {
    const start = scalar(query.start)
    const end = scalar(query.end)
    if (start && end && isDate(start) && isDate(end) && start < end) {
      state.start = start
      state.end = end
    } else {
      Object.assign(state, defaultStatisticsState(today))
    }
  }
  return { state, query: serializeStatisticsState(state, today) }
}

export function compactQuery(query: QueryRecord): Record<string, string> {
  return Object.fromEntries(Object.entries(query).filter((entry): entry is [string, string] => entry[1] !== undefined))
}

export function queriesEqual(left: QueryInput, right: QueryRecord): boolean {
  const normalize = (value: QueryInput | QueryRecord) => Object.entries(value)
    .filter(([, item]) => item !== undefined)
    .sort(([a], [b]) => a.localeCompare(b))
  return JSON.stringify(normalize(left)) === JSON.stringify(normalize(right))
}
