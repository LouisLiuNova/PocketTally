import type {
  CalendarStatistics,
  CashFlow,
  CategoryStatistics,
  ExpenseTransactionPage,
  Expenses,
  Overview,
  TagStatistics,
} from '~/types/ledger'
import type { StatisticsRouteState } from '~/utils/routeQuery'

export interface StatisticsSnapshot {
  state: StatisticsRouteState
  overview: Overview
  cashFlow: CashFlow
  expenses: Expenses
  categoryStatistics: CategoryStatistics
  tagStatistics: TagStatistics
  calendar: CalendarStatistics
}

export interface StatisticsDrilldownState {
  title: string
  query: Record<string, string | boolean>
  data: ExpenseTransactionPage | null
  error: string
  loading: boolean
}
