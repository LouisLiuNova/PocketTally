<script setup lang="ts">
import type {
  CalendarStatistics,
  CashFlow,
  CategoryStatistics,
  ExpenseTransactionPage,
  Expenses,
  Overview,
  TagStatistics,
} from '~/types/ledger'
import { errorMessage } from '~/composables/useLedger'
import {
  compactQuery,
  defaultStatisticsState,
  defaultTransactionState,
  isDate,
  nextDate,
  parseStatisticsQuery,
  queriesEqual,
  serializeStatisticsState,
  serializeTransactionState,
  statisticsPeriod,
  type StatisticsRouteState,
  type StatisticsPreset,
} from '~/utils/routeQuery'
import { localInput, money } from '~/utils/money'

const route = useRoute()
const workspace = useLedgerWorkspace()
const today = localInput().slice(0, 10)
const overview = ref<Overview | null>(null)
const cashFlow = ref<CashFlow | null>(null)
const expenses = ref<Expenses | null>(null)
const categoryStatistics = ref<CategoryStatistics | null>(null)
const tagStatistics = ref<TagStatistics | null>(null)
const calendar = ref<CalendarStatistics | null>(null)
const loading = ref(false)
const queryError = ref('')
const customError = ref('')
const customStartDraft = ref('')
const customEndDraft = ref('')
const loadedData = ref(false)
const drill = ref<{ title: string; data: ExpenseTransactionPage } | null>(null)
const drillLoading = ref(false)
let requestId = 0
let stopRouteWatch: (() => void) | undefined

const routeState = computed(() => parseStatisticsQuery(route.query, today).state)
const period = computed(() => statisticsPeriod(routeState.value, today))
const trendMax = computed(() => Math.max(1, ...(cashFlow.value?.buckets.flatMap(item => [item.incomeAmountMinor, item.expenseAmountMinor, Math.abs(item.netCashFlowMinor)]) || [1])))
const categoryMax = computed(() => Math.max(1, ...(categoryStatistics.value?.items.map(item => Math.abs(item.amountMinor)) || [1])))
const calendarMax = computed(() => Math.max(1, ...(calendar.value?.days.map(day => Math.abs(day.netCashFlowMinor)) || [1])))
const expenseCategories = computed(() => workspace.categories.value.filter(category => category.purpose === 'expense' && !category.parentCategory))
const hasAnalysisData = computed(() => {
  return !!cashFlow.value?.buckets.some(item => item.incomeAmountMinor || item.refundAmountMinor || item.expenseAmountMinor || item.netCashFlowMinor)
    || !!expenses.value?.buckets.some(item => item.netExpenseMinor)
    || !!categoryStatistics.value?.items.some(item => item.amountMinor || item.directAmountMinor)
    || !!tagStatistics.value?.items.some(item => item.netExpenseMinor)
})

function formatChange(value: number | null) {
  return value === null ? '上期为 0，暂无百分比' : `${value >= 0 ? '+' : ''}${value.toFixed(1)}% 较上期`
}

function bucketLabel(value: string) {
  return localInput(value).slice(0, 10)
}

function selectValue(event: Event) {
  return (event.target as HTMLSelectElement).value
}

async function updateRoute(patch: Partial<StatisticsRouteState>, replace = false) {
  const next = { ...routeState.value, ...patch }
  return navigateTo(
    { path: '/statistics', query: compactQuery(serializeStatisticsState(next, today)) },
    { replace },
  )
}

function setPreset(preset: StatisticsPreset) {
  if (preset === 'custom') {
    const defaults = defaultStatisticsState(today)
    void updateRoute({ preset, start: defaults.start, end: defaults.end })
  } else {
    void updateRoute({ preset })
  }
}

function commitCustomDates() {
  customError.value = ''
  if (!isDate(customStartDraft.value) || !isDate(customEndDraft.value)) {
    customError.value = '自定义范围需要有效的开始和结束日期。'
    return
  }
  if (customStartDraft.value >= customEndDraft.value) {
    customError.value = '统计开始日期必须早于结束日期。'
    return
  }
  void updateRoute({ preset: 'custom', start: customStartDraft.value, end: customEndDraft.value })
}

async function loadStatistics(state = routeState.value) {
  const currentRequest = ++requestId
  const selectedPeriod = statisticsPeriod(state, today)
  const withGranularity = { ...selectedPeriod, granularity: state.granularity }
  loading.value = true
  queryError.value = ''
  try {
    const [summary, flow, expenseTrend, categoryData, tagData, calendarData] = await Promise.all([
      $fetch<Overview>('/api/v1/statistics/overview', { query: selectedPeriod }),
      $fetch<CashFlow>('/api/v1/statistics/cash-flow', { query: withGranularity }),
      $fetch<Expenses>('/api/v1/statistics/expenses', { query: withGranularity }),
      $fetch<CategoryStatistics>('/api/v1/statistics/categories', { query: { ...withGranularity, parentCategoryId: state.parentCategoryId || undefined } }),
      $fetch<TagStatistics>('/api/v1/statistics/tags', { query: selectedPeriod }),
      $fetch<CalendarStatistics>('/api/v1/statistics/calendar', { query: { month: state.month } }),
    ])
    if (currentRequest !== requestId) return
    overview.value = summary
    cashFlow.value = flow
    expenses.value = expenseTrend
    categoryStatistics.value = categoryData
    tagStatistics.value = tagData
    calendar.value = calendarData
    loadedData.value = true
  } catch (error) {
    if (currentRequest === requestId) queryError.value = errorMessage(error)
  } finally {
    if (currentRequest === requestId) loading.value = false
  }
}

async function synchronizeRoute() {
  const parsed = parseStatisticsQuery(route.query, today)
  if (!queriesEqual(route.query, parsed.query)) {
    await navigateTo({ path: '/statistics', query: compactQuery(parsed.query) }, { replace: true })
    return
  }
  customStartDraft.value = parsed.state.start
  customEndDraft.value = parsed.state.end
  customError.value = ''
  drill.value = null
  await loadStatistics(parsed.state)
}

function showTransactions(start: string, end: string) {
  const state = defaultTransactionState(today)
  state.start = start
  state.end = end
  return navigateTo({ path: '/transactions', query: compactQuery(serializeTransactionState(state, today)) })
}

function showCalendarDay(date: string) {
  return showTransactions(date, nextDate(date))
}

function showCashBucket(startAt: string, endAt: string) {
  return showTransactions(bucketLabel(startAt), bucketLabel(endAt))
}

async function openExpenseDrill(title: string, query: Record<string, string | boolean>) {
  const currentPeriod = period.value
  drillLoading.value = true
  queryError.value = ''
  try {
    const data = await $fetch<ExpenseTransactionPage>('/api/v1/statistics/expense-transactions', {
      query: { ...currentPeriod, page: 1, pageSize: 100, ...query },
    })
    drill.value = { title, data }
  } catch (error) {
    queryError.value = errorMessage(error)
  } finally {
    drillLoading.value = false
  }
}

onMounted(() => {
  stopRouteWatch = watch(() => route.fullPath, () => void synchronizeRoute(), { immediate: true })
})
watch(workspace.refreshRevision, () => void loadStatistics())
onBeforeUnmount(() => {
  requestId++
  stopRouteWatch?.()
})
</script>

<template>
  <div class="page-flow page-flow--statistics">
  <div class="view-toolbar analytics-toolbar">
    <div class="period-tabs">
      <button v-for="item in [{ value: 'this_month', label: '本月' }, { value: 'last_month', label: '上月' }, { value: 'year', label: '今年' }, { value: 'twelve_months', label: '近 12 个月' }, { value: 'custom', label: '自定义' }]" :key="item.value" :class="{ active: routeState.preset === item.value }" @click="setPreset(item.value as StatisticsPreset)">{{ item.label }}</button>
    </div>
    <template v-if="routeState.preset === 'custom'">
      <label>开始<input v-model="customStartDraft" type="date" @change="commitCustomDates"></label>
      <label>结束（不含）<input v-model="customEndDraft" type="date" @change="commitCustomDates"></label>
    </template>
    <label>粒度<select :value="routeState.granularity" @change="updateRoute({ granularity: selectValue($event) as StatisticsRouteState['granularity'] })"><option value="day">日</option><option value="week">周</option><option value="month">月</option></select></label>
    <label>父分类<select :value="routeState.parentCategoryId" @change="updateRoute({ parentCategoryId: selectValue($event) })"><option value="">全部一级分类</option><option v-for="category in expenseCategories" :key="category.id" :value="category.id">{{ category.name }}</option></select></label>
  </div>
  <p v-if="customError" role="alert" class="error-box">{{ customError }}</p>
  <div v-if="queryError" role="alert" class="error-box">{{ queryError }}<UButton label="重试" color="neutral" @click="loadStatistics" /></div>
  <p v-if="loading && !loadedData" role="status" class="empty-state">正在读取统计分析…</p>

  <section v-if="overview" class="metric-grid statistics-metrics">
    <article class="metric-card feature"><span>实际净现金流</span><strong>{{ money(overview.netCashFlow.currentAmountMinor) }}</strong><p>{{ formatChange(overview.netCashFlow.changePercent) }}</p></article>
    <article class="metric-card"><span>普通收入</span><strong>{{ money(overview.income.currentAmountMinor) }}</strong><p>{{ formatChange(overview.income.changePercent) }}</p></article>
    <article class="metric-card"><span>消费净支出</span><strong>{{ money(overview.netExpense.currentAmountMinor) }}</strong><p>{{ formatChange(overview.netExpense.changePercent) }}</p></article>
  </section>

  <section v-if="loadedData && !hasAnalysisData" class="panel">
    <h2>当前筛选范围暂无可分析数据</h2>
    <p class="hint">可以调整时间范围，或先记录一笔交易后再回来查看变化。</p>
    <div class="composer-actions"><UButton color="neutral" variant="outline" label="调整范围" @click="navigateTo('/statistics')" /><UButton label="记一笔" icon="i-lucide-plus" @click="workspace.transactionEditor.value = {}" /></div>
  </section>

  <template v-if="loadedData && hasAnalysisData">
    <UPageGrid as="div" class="page-grid analytics-grid">
      <section class="panel analytics-trend">
        <div class="panel-head"><h2>现金流趋势</h2><span class="hint">点击时间桶查看流水</span></div>
        <div class="real-trend" tabindex="0" aria-label="可按时间桶查看现金流"><button v-for="item in cashFlow?.buckets" :key="item.startAt" class="trend-row bucket-button" @click="showCashBucket(item.startAt, item.endAt)"><span>{{ bucketLabel(item.startAt).slice(5) }}</span><div><div class="trend-track"><i :style="{ width: `${item.incomeAmountMinor / trendMax * 100}%` }" /></div><div class="trend-track expense-track"><i :style="{ width: `${item.expenseAmountMinor / trendMax * 100}%` }" /></div></div><small>{{ money(item.incomeAmountMinor) }} / 退款 {{ money(item.refundAmountMinor) }} / 支出 {{ money(item.expenseAmountMinor) }} / 净额 {{ money(item.netCashFlowMinor) }}</small></button></div>
      </section>
      <section class="panel analytics-expense">
        <div class="panel-head"><h2>消费趋势</h2><span class="hint">点击时间桶查看净额明细</span></div>
        <p v-if="!expenses?.buckets.length" class="empty-state">本期暂无消费</p>
        <button v-for="item in expenses?.buckets" :key="item.startAt" class="resource-row drill-button" @click="openExpenseDrill(bucketLabel(item.startAt), { startDate: bucketLabel(item.startAt), endDate: bucketLabel(item.endAt) })"><span>{{ bucketLabel(item.startAt) }}</span><span>{{ money(item.netExpenseMinor) }} / 累计 {{ money(item.cumulativeNetExpenseMinor) }}</span></button>
      </section>
      <section class="panel analytics-category">
        <div class="panel-head"><h2>分类分析</h2><button v-if="routeState.parentCategoryId" class="text-link" @click="updateRoute({ parentCategoryId: '' })">返回一级分类</button></div>
        <p class="hint">退款按原支出日期抵减；点击分类查看净额明细。</p>
        <button v-for="item in categoryStatistics?.items" :key="item.categoryId" class="category-stat" @click="openExpenseDrill(item.name, { categoryId: item.categoryId, includeDescendants: true })"><span><strong>{{ item.name }}</strong><small>直接 {{ money(item.directAmountMinor) }} · 变化贡献 {{ money(item.changeContributionMinor) }}</small></span><i :style="{ width: `${Math.abs(item.amountMinor) / categoryMax * 100}%` }" /><b>{{ money(item.amountMinor) }}</b></button>
        <div v-for="parent in categoryStatistics?.items.filter(item => item.children.length)" :key="`${parent.categoryId}-children`" class="child-links"><span>{{ parent.name }} 下钻：</span><button v-for="child in parent.children" :key="child.categoryId" @click="openExpenseDrill(`${parent.name} / ${child.name}`, { categoryId: child.categoryId, includeDescendants: true })">{{ child.name }} {{ money(child.amountMinor) }}</button></div>
      </section>
      <section class="panel analytics-tags">
        <h2>Tag 汇总</h2><p class="hint">一笔交易可完整计入多个 Tag，因此不提供 Tag 合计或占比。</p>
        <button v-for="item in tagStatistics?.items" :key="item.tagId" class="resource-row drill-button" @click="openExpenseDrill(`Tag：${item.name}`, { tagId: item.tagId })"><span><i class="color-dot" :style="{ background: item.color }" />{{ item.name }}</span><strong>{{ money(item.netExpenseMinor) }}</strong></button>
      </section>
      <section class="panel calendar-panel analytics-calendar">
        <div class="panel-head"><div><h2>收支日历</h2><p class="hint">点击日期查看服务端筛选的当日流水</p></div><label>月份 <input :value="routeState.month" type="month" @change="updateRoute({ month: selectValue($event) })"></label></div>
        <div class="calendar-grid"><button v-for="day in calendar?.days" :key="day.date" :style="{ '--heat': `${Math.abs(day.netCashFlowMinor) / calendarMax * 18}%` }" @click="showCalendarDay(day.date)"><b>{{ day.date.slice(-2) }}</b><span>{{ money(day.netCashFlowMinor) }}</span><small>入 {{ money(day.incomeAmountMinor + day.refundAmountMinor) }} / 出 {{ money(day.expenseAmountMinor) }}</small></button></div>
      </section>
    </UPageGrid>
    <section v-if="drill || drillLoading" class="panel drill-panel">
      <div class="panel-head"><h2>{{ drill?.title || '正在读取明细…' }}</h2><button class="text-link" @click="drill = null">关闭</button></div>
      <template v-if="drill"><p class="hint">原支出 {{ money(drill.data.totals.originalAmountMinor) }} − 有效退款 {{ money(drill.data.totals.refundedAmountMinor) }} = 净支出 {{ money(drill.data.totals.netExpenseMinor) }}；共 {{ drill.data.total }} 笔。</p><button v-for="item in drill.data.items" :key="item.transaction.id" class="mvp-transaction" @click="workspace.openTransaction(item.transaction.id)"><span class="transaction-icon blue">支出</span><span><strong>{{ item.transaction.description || '支出' }}</strong><small>原支出 {{ money(item.originalAmountMinor) }} · 已退 {{ money(item.refundedAmountMinor) }}</small></span><time>{{ localInput(item.transaction.occurredAt).replace('T', ' ') }}</time><b>{{ money(item.netExpenseMinor) }}</b></button></template>
    </section>
  </template>
  </div>
</template>
