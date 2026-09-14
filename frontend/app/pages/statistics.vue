<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type {
  CalendarStatistics,
  CashFlow,
  CategoryStatistics,
  ExpenseTransactionPage,
  Overview,
  TagStatistics,
} from '~/types/ledger'
import type { StatisticsDrilldownState } from '~/types/statisticsWorkspace'
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
import { cashFlowSummary } from '~/utils/cashFlowTrend'
import { metricIcons } from '~/constants/metricIcons'

const route = useRoute()
const workspace = useLedgerWorkspace()
const today = localInput().slice(0, 10)
const overview = ref<Overview | null>(null)
const cashFlow = ref<CashFlow | null>(null)
const categoryStatistics = ref<CategoryStatistics | null>(null)
const tagStatistics = ref<TagStatistics | null>(null)
const calendar = ref<CalendarStatistics | null>(null)
const loading = ref(false)
const queryError = ref('')
const customError = ref('')
const customStartDraft = ref('')
const customEndDraft = ref('')
const loadedData = ref(false)
const snapshotState = ref<StatisticsRouteState | null>(null)
const drill = ref<StatisticsDrilldownState | null>(null)
let requestId = 0
let stopRouteWatch: (() => void) | undefined

const routeState = computed(() => parseStatisticsQuery(route.query, today).state)
const period = computed(() => statisticsPeriod(routeState.value, today))
const categoryMax = computed(() => Math.max(1, ...(categoryStatistics.value?.items.map(item => Math.abs(item.amountMinor)) || [1])))
const cashFlowTotals = computed(() => cashFlowSummary(cashFlow.value?.buckets || []))
const expenseCategories = computed(() => workspace.categories.value.filter(category => category.purpose === 'expense' && !category.parentCategory))
const hasAnalysisData = computed(() => {
  return !!cashFlow.value?.buckets.some(item => item.incomeAmountMinor || item.refundAmountMinor || item.expenseAmountMinor || item.netCashFlowMinor)
    || !!categoryStatistics.value?.items.some(item => item.amountMinor || item.directAmountMinor)
    || !!tagStatistics.value?.items.some(item => item.netExpenseMinor)
})
const snapshotPeriod = computed(() => snapshotState.value ? statisticsPeriod(snapshotState.value, today) : null)
const showingPreviousSnapshot = computed(() => loadedData.value && !!snapshotState.value && JSON.stringify(snapshotState.value) !== JSON.stringify(routeState.value))
const calendarCells = computed(() => {
  const days = calendar.value?.days || []
  const first = days[0]
  if (!first) return []
  const weekday = new Date(`${first.date}T00:00:00Z`).getUTCDay()
  const offset = weekday === 0 ? 6 : weekday - 1
  return [...Array.from({ length: offset }, () => null), ...days]
})
const presetItems = [
  { value: 'this_month', label: '本月' },
  { value: 'last_month', label: '上月' },
  { value: 'year', label: '今年' },
  { value: 'twelve_months', label: '近 12 个月' },
  { value: 'custom', label: '自定义' },
]
const granularityItems = [
  { value: 'day', label: '日' },
  { value: 'week', label: '周' },
  { value: 'month', label: '月' },
]
const weekdayLabels = ['一', '二', '三', '四', '五', '六', '日']
const categoryColumns: TableColumn<CategoryStatistics['items'][number]>[] = [
  { accessorKey: 'name', header: '分类' },
  { accessorKey: 'amountMinor', header: '净额' },
  { accessorKey: 'actions', header: '操作' },
]
const tagColumns: TableColumn<TagStatistics['items'][number]>[] = [
  { accessorKey: 'name', header: 'Tag' },
  { accessorKey: 'netExpenseMinor', header: '净支出' },
  { accessorKey: 'actions', header: '操作' },
]

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
    const [summary, flow, categoryData, tagData, calendarData] = await Promise.all([
      $fetch<Overview>('/api/v1/statistics/overview', { query: selectedPeriod }),
      $fetch<CashFlow>('/api/v1/statistics/cash-flow', { query: withGranularity }),
      $fetch<CategoryStatistics>('/api/v1/statistics/categories', { query: { ...withGranularity, parentCategoryId: state.parentCategoryId || undefined } }),
      $fetch<TagStatistics>('/api/v1/statistics/tags', { query: selectedPeriod }),
      $fetch<CalendarStatistics>('/api/v1/statistics/calendar', { query: { month: state.month } }),
    ])
    if (currentRequest !== requestId) return
    overview.value = summary
    cashFlow.value = flow
    categoryStatistics.value = categoryData
    tagStatistics.value = tagData
    calendar.value = calendarData
    snapshotState.value = state
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
  return navigateTo({
    path: '/transactions',
    query: { ...compactQuery(serializeTransactionState(state, today)), start: state.start, end: state.end },
  })
}

function showCalendarDay(date: string) {
  return showTransactions(date, nextDate(date))
}

function showCashBucket(startAt: string, endAt: string) {
  return showTransactions(bucketLabel(startAt), bucketLabel(endAt))
}

async function openExpenseDrill(title: string, query: Record<string, string | boolean>) {
  const currentPeriod = period.value
  drill.value = { title, query, data: null, error: '', loading: true }
  try {
    const data = await $fetch<ExpenseTransactionPage>('/api/v1/statistics/expense-transactions', {
      query: { ...currentPeriod, page: 1, pageSize: 100, ...query },
    })
    if (drill.value?.title === title) drill.value = { title, query, data, error: '', loading: false }
  } catch (error) {
    if (drill.value?.title === title) drill.value = { title, query, data: null, error: errorMessage(error), loading: false }
  }
}

function closeDrill() {
  drill.value = null
}

function retryDrill() {
  if (!drill.value) return
  void openExpenseDrill(drill.value.title, drill.value.query)
}

function openDrillTransaction(id: string) {
  closeDrill()
  void nextTick(() => workspace.openTransaction(id))
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
  <div class="page-flow page-flow--statistics" :aria-busy="loading">
  <section class="statistics-toolbar" aria-label="统计筛选">
    <div class="statistics-toolbar__periods">
      <p class="mb-2 text-sm font-medium text-highlighted">时间范围</p>
      <UTabs :items="presetItems" :model-value="routeState.preset" activation-mode="manual" :content="false" @update:model-value="value => setPreset(value as StatisticsPreset)" />
    </div>
    <div class="statistics-toolbar__controls">
      <UFormField v-if="routeState.preset === 'custom'" label="开始日期" name="statistics-start">
        <UInput id="statistics-start" v-model="customStartDraft" type="date" />
      </UFormField>
      <UFormField v-if="routeState.preset === 'custom'" label="结束日期（不含）" name="statistics-end">
        <UInput id="statistics-end" v-model="customEndDraft" type="date" />
      </UFormField>
      <UButton v-if="routeState.preset === 'custom'" color="neutral" variant="outline" label="应用日期" @click="commitCustomDates" />
      <UFormField label="粒度" name="statistics-granularity">
        <USelect :model-value="routeState.granularity" :items="granularityItems" @update:model-value="value => updateRoute({ granularity: value as StatisticsRouteState['granularity'] })" />
      </UFormField>
      <UFormField label="父分类" name="statistics-parent-category">
        <USelect :model-value="routeState.parentCategoryId || '__all__'" :items="[{ value: '__all__', label: '全部一级分类' }, ...expenseCategories.map(category => ({ value: category.id, label: category.name }))]" @update:model-value="value => updateRoute({ parentCategoryId: value === '__all__' ? '' : String(value || '') })" />
      </UFormField>
    </div>
  </section>
  <UAlert v-if="customError" color="error" variant="soft" icon="i-lucide-circle-alert" title="日期范围无效" :description="customError" role="alert" />
  <UAlert v-if="queryError" color="error" variant="soft" icon="i-lucide-circle-alert" title="统计读取失败" :description="snapshotPeriod ? `${queryError} 当前仍显示 ${snapshotPeriod.startDate} 至 ${snapshotPeriod.endDate} 的结果。` : queryError" role="alert">
    <template #actions><UButton label="重试" color="error" variant="soft" :loading="loading" @click="loadStatistics" /></template>
  </UAlert>
  <UAlert v-if="showingPreviousSnapshot && !queryError" color="info" variant="soft" icon="i-lucide-refresh-cw" title="正在更新统计" description="筛选条件已更新，当前暂显示上一组完整结果。" role="status" />
  <div v-if="loading && !loadedData" class="statistics-loading" role="status" aria-label="正在读取统计分析">
    <div class="grid grid-cols-1 gap-4 md:grid-cols-3"><USkeleton v-for="index in 3" :key="index" class="h-32 w-full" /></div>
    <USkeleton class="h-80 w-full" />
  </div>

  <section v-if="overview" class="grid grid-cols-1 gap-4 md:grid-cols-3" aria-label="统计对比摘要">
    <MetricSummaryCard label="实际净现金流" :value="money(overview.netCashFlow.currentAmountMinor)" :comparison="formatChange(overview.netCashFlow.changePercent)" emphasis :icon="metricIcons.cashFlow" />
    <MetricSummaryCard label="普通收入" :value="money(overview.income.currentAmountMinor)" :comparison="formatChange(overview.income.changePercent)" icon="i-lucide-arrow-down-left" />
    <MetricSummaryCard label="消费净支出" :value="money(overview.netExpense.currentAmountMinor)" :comparison="formatChange(overview.netExpense.changePercent)" icon="i-lucide-arrow-up-right" />
  </section>

  <UEmpty
    v-if="loadedData && !hasAnalysisData"
    icon="i-lucide-chart-no-axes-combined"
    title="当前筛选范围暂无可分析数据"
    description="可以调整时间范围，或先记录一笔交易后再回来查看变化。"
    variant="subtle"
  >
    <template #actions>
      <UButton color="neutral" variant="outline" label="恢复本月" @click="navigateTo('/statistics')" />
      <UButton label="记一笔" icon="i-lucide-plus" @click="workspace.transactionEditor.value = {}" />
    </template>
  </UEmpty>

  <template v-if="loadedData && hasAnalysisData">
    <div class="grid min-w-0 grid-cols-1 gap-5 lg:grid-cols-2" aria-label="统计分析区">
      <UCard data-statistics-section="cash-flow" class="min-w-0 lg:col-span-2" variant="outline">
        <template #header><div class="flex items-start justify-between gap-4"><div><h2 class="m-0 text-base font-semibold text-highlighted">现金流趋势</h2><p class="mt-1 text-xs text-muted">点击时间桶查看流水</p></div></div></template>
        <div class="grid grid-cols-2 gap-3 md:grid-cols-4" aria-label="当前范围现金流汇总">
          <div v-for="item in [{ label: '普通收入', value: cashFlowTotals.incomeAmountMinor }, { label: '退款流入', value: cashFlowTotals.refundAmountMinor }, { label: '支出流出', value: cashFlowTotals.expenseAmountMinor }, { label: '净现金流', value: cashFlowTotals.netCashFlowMinor }]" :key="item.label" class="border-l-2 border-primary pl-2"><span class="block text-xs text-muted">{{ item.label }}</span><strong class="mt-1 block tabular-nums">{{ money(item.value) }}</strong></div>
        </div>
        <UAlert v-if="!cashFlowTotals.formulaMatchesApi" class="mt-4" color="error" variant="soft" icon="i-lucide-circle-alert" title="现金流数据不一致" description="净额与分项合计不一致，请重试后再查看。" role="alert" />
        <LazyCashFlowTrend :buckets="cashFlow?.buckets || []" :granularity="routeState.granularity" variant="full" @drilldown="showCashBucket" />
      </UCard>

      <UCard data-statistics-section="category" variant="outline">
        <template #header><div class="flex items-start justify-between gap-4"><div><h2 class="m-0 text-base font-semibold text-highlighted">分类分析</h2><p class="mt-1 text-xs text-muted">退款按原支出日期抵减</p></div><UButton v-if="routeState.parentCategoryId" color="neutral" variant="link" label="返回一级分类" @click="updateRoute({ parentCategoryId: '' })" /></div></template>
        <UTable :data="categoryStatistics?.items || []" :columns="categoryColumns" caption="分类分析" :ui="{ td: 'align-middle' }" empty="暂无分类数据">
          <template #name-cell="{ row }"><div class="min-w-0"><strong class="block text-highlighted">{{ row.original.name }}</strong><small class="block text-muted">直接 {{ money(row.original.directAmountMinor) }} · 变化贡献 {{ money(row.original.changeContributionMinor) }}</small></div></template>
          <template #amountMinor-cell="{ row }"><strong class="tabular-nums">{{ money(row.original.amountMinor) }}</strong></template>
          <template #actions-cell="{ row }"><UButton color="neutral" variant="ghost" size="sm" label="查看明细" @click="openExpenseDrill(row.original.name, { categoryId: row.original.categoryId, includeDescendants: true })" /></template>
        </UTable>
        <div v-for="parent in categoryStatistics?.items.filter(item => item.children.length)" :key="`${parent.categoryId}-children`" class="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted"><span>{{ parent.name }} 下钻：</span><UButton v-for="child in parent.children" :key="child.categoryId" color="neutral" variant="outline" size="xs" :label="`${child.name} ${money(child.amountMinor)}`" @click="openExpenseDrill(`${parent.name} / ${child.name}`, { categoryId: child.categoryId, includeDescendants: true })" /></div>
      </UCard>

      <UCard data-statistics-section="tags" variant="outline">
        <template #header><div><h2 class="m-0 text-base font-semibold text-highlighted">Tag 汇总</h2><p class="mt-1 text-xs text-muted">一笔交易可完整计入多个 Tag，不提供 Tag 合计或占比。</p></div></template>
        <UTable :data="tagStatistics?.items || []" :columns="tagColumns" caption="Tag 汇总" :ui="{ td: 'align-middle' }" empty="暂无 Tag 数据">
          <template #name-cell="{ row }"><span class="inline-flex items-center gap-2"><i class="size-2 rounded-full" :style="{ background: row.original.color }" aria-hidden="true" />{{ row.original.name }}</span></template>
          <template #netExpenseMinor-cell="{ row }"><strong class="tabular-nums">{{ money(row.original.netExpenseMinor) }}</strong></template>
          <template #actions-cell="{ row }"><UButton color="neutral" variant="ghost" size="sm" label="查看明细" @click="openExpenseDrill(`Tag：${row.original.name}`, { tagId: row.original.tagId })" /></template>
        </UTable>
      </UCard>

      <UCard data-statistics-section="calendar" variant="outline">
        <template #header><div class="flex items-start justify-between gap-4"><div><h2 class="m-0 text-base font-semibold text-highlighted">收支日历</h2><p class="mt-1 text-xs text-muted">点击日期查看服务端筛选的当日流水</p></div><UFormField label="月份" name="statistics-month"><UInput :model-value="routeState.month" type="month" @change="updateRoute({ month: selectValue($event) })" /></UFormField></div></template>
        <div class="calendar-grid calendar-grid--weekdays" aria-hidden="true"><span v-for="weekday in weekdayLabels" :key="weekday" class="calendar-weekday">{{ weekday }}</span></div>
        <div class="calendar-grid"><span v-for="(day, index) in calendarCells" :key="day?.date || `blank-${index}`" :class="{ 'calendar-grid__blank': !day }" :aria-hidden="day ? undefined : 'true'"><template v-if="day"><button :aria-label="`${day.date}，净现金流 ${money(day.netCashFlowMinor)}，流入 ${money(day.incomeAmountMinor + day.refundAmountMinor)}，退款 ${money(day.refundAmountMinor)}，支出 ${money(day.expenseAmountMinor)}`" @click="showCalendarDay(day.date)"><b>{{ day.date.slice(-2) }}</b><span v-if="day.incomeAmountMinor + day.refundAmountMinor" class="calendar-day-inflow">+{{ money(day.incomeAmountMinor + day.refundAmountMinor) }}</span><span v-if="day.expenseAmountMinor" class="calendar-day-outflow">−{{ money(day.expenseAmountMinor) }}</span><small v-if="!day.incomeAmountMinor && !day.refundAmountMinor && !day.expenseAmountMinor" class="calendar-day-empty">无收支</small></button></template></span></div>
      </UCard>
    </div>
  </template>
  <StatisticsDrillover v-if="drill" :open="!!drill" :title="drill.title" :loading="drill.loading" :error="drill.error" :data="drill.data" @close="closeDrill" @retry="retryDrill" @open-transaction="openDrillTransaction" />
  </div>
</template>

<style scoped>
.statistics-toolbar {
  display: grid;
  gap: 16px;
  padding: 16px;
  border: 1px solid var(--ui-border-muted);
  border-radius: 12px;
  background: var(--ui-bg-elevated);
}

.statistics-toolbar__periods,
.statistics-toolbar__controls {
  min-width: 0;
}

.statistics-toolbar__controls {
  display: flex;
  align-items: end;
  flex-wrap: wrap;
  gap: 12px;
}

.statistics-toolbar__controls > [data-slot="form-field"] {
  min-width: 150px;
}

.statistics-loading {
  display: grid;
  gap: 20px;
}

.calendar-grid--weekdays {
  margin-top: 0;
  margin-bottom: 8px;
}

.calendar-weekday {
  color: var(--ui-text-muted);
  font-size: 11px;
  text-align: center;
}

.calendar-grid__blank {
  min-width: 0;
}

.calendar-grid__blank:not(:has(button)) {
  min-height: 78px;
}

@media (hover: hover) and (pointer: fine) {
  .calendar-grid button:not(:disabled):hover {
    box-shadow: var(--pt-elevation-button-hover);
  }
}

@media (prefers-reduced-motion: reduce) {
  .calendar-grid button {
    transition: none;
  }
}

@media (max-width: 720px) {
  .calendar-grid {
    min-width: 0;
    grid-template-columns: repeat(7, minmax(0, 1fr));
  }

  .calendar-grid button {
    min-height: 70px;
    padding: 7px;
  }
}

@media (min-width: 900px) {
  .statistics-toolbar {
    grid-template-columns: minmax(280px, 1fr) auto;
    align-items: end;
  }

  .statistics-toolbar__controls {
    justify-content: flex-end;
  }
}
</style>
