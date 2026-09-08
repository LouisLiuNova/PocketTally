import type {
  Account, CalendarStatistics, CashFlow, Category, CategoryStatistics, Expenses,
  Granularity, Overview, Page, Tag, TagStatistics, Transaction,
} from '~/types/ledger'

export function errorMessage(error: any): string {
  const data = error?.data
  if (data?.message) {
    const fields = Array.isArray(data.details) ? data.details.map((item: any) => item.msg).filter(Boolean).join('；') : ''
    return fields ? `${data.message}：${fields}` : data.message
  }
  return '无法连接账本服务，请检查服务后重试。'
}

export interface TransactionQuery {
  page: number; pageSize: number; startAt?: string; endAt?: string; type?: string; accountId?: string
  categoryId?: string; includeDescendants?: boolean; tagId?: string; q?: string; status?: string
}

export interface StatisticsQuery {
  startDate: string; endDate: string; granularity: Granularity; month: string; parentCategoryId?: string
}

export function useLedger() {
  const accounts = ref<Account[]>([])
  const categories = ref<Category[]>([])
  const tags = ref<Tag[]>([])
  const transactions = ref<Transaction[]>([])
  const transactionTotal = ref(0)
  const overview = ref<Overview | null>(null)
  const cashFlow = ref<CashFlow | null>(null)
  const expenses = ref<Expenses | null>(null)
  const categoryStatistics = ref<CategoryStatistics | null>(null)
  const tagStatistics = ref<TagStatistics | null>(null)
  const calendar = ref<CalendarStatistics | null>(null)
  const loading = ref(false)
  const loadError = ref('')
  const loaded = ref(false)

  async function refreshResources() {
    const [a, c, t] = await Promise.all([
      $fetch<Account[]>('/api/v1/accounts'), $fetch<Category[]>('/api/v1/categories'), $fetch<Tag[]>('/api/v1/tags'),
    ])
    accounts.value = a; categories.value = c; tags.value = t
  }

  async function loadTransactions(query: TransactionQuery) {
    const result = await $fetch<Page<Transaction>>('/api/v1/transactions', { query })
    transactions.value = result.items
    transactionTotal.value = result.total
  }

  async function loadStatistics(query: StatisticsQuery) {
    const period = { startDate: query.startDate, endDate: query.endDate }
    const withGranularity = { ...period, granularity: query.granularity }
    const [summary, flow, expenseTrend, categoryData, tagData, calendarData] = await Promise.all([
      $fetch<Overview>('/api/v1/statistics/overview', { query: period }),
      $fetch<CashFlow>('/api/v1/statistics/cash-flow', { query: withGranularity }),
      $fetch<Expenses>('/api/v1/statistics/expenses', { query: withGranularity }),
      $fetch<CategoryStatistics>('/api/v1/statistics/categories', { query: { ...withGranularity, parentCategoryId: query.parentCategoryId } }),
      $fetch<TagStatistics>('/api/v1/statistics/tags', { query: period }),
      $fetch<CalendarStatistics>('/api/v1/statistics/calendar', { query: { month: query.month } }),
    ])
    overview.value = summary; cashFlow.value = flow; expenses.value = expenseTrend
    categoryStatistics.value = categoryData; tagStatistics.value = tagData; calendar.value = calendarData
  }

  async function refresh(transactionQuery: TransactionQuery, statisticsQuery: StatisticsQuery) {
    if (loading.value) return
    loading.value = true; loadError.value = ''
    try {
      await Promise.all([refreshResources(), loadTransactions(transactionQuery), loadStatistics(statisticsQuery)])
      loaded.value = true
    } catch (error) { loadError.value = errorMessage(error) }
    finally { loading.value = false }
  }

  return {
    accounts, categories, tags, transactions, transactionTotal, overview, cashFlow, expenses,
    categoryStatistics, tagStatistics, calendar, loading, loadError, loaded,
    refreshResources, loadTransactions, loadStatistics, refresh,
  }
}
