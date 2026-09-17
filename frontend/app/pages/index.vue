<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import { kindLabels, type CashFlow, type CategoryStatistics, type Overview, type Page, type Transaction } from '~/types/ledger'
import { errorMessage, type TransactionQuery } from '~/composables/useLedger'
import { defaultTransactionState, monthPeriod, serializeTransactionState } from '~/utils/routeQuery'
import { localInput, minor, money } from '~/utils/money'
import { accountNames, signedAmount } from '~/utils/transactionDisplay'
import { metricIcons } from '~/constants/metricIcons'

const workspace = useLedgerWorkspace()
const today = localInput().slice(0, 10)
const requestFetch = useRequestFetch()
const period = monthPeriod(today)
const transactionQuery: TransactionQuery = {
  page: 1,
  pageSize: 20,
  startAt: new Date(`${period.start}T00:00:00+08:00`).toISOString(),
  endAt: new Date(`${period.end}T00:00:00+08:00`).toISOString(),
  status: 'active',
}
const { data, pending: loading, error, refresh } = useAsyncData('dashboard-overview', async (_nuxtApp, { signal }) => {
  const [transactionData, overview, categoryStatistics] = await Promise.all([
    requestFetch<Page<Transaction>>('/api/v1/transactions', { query: transactionQuery, signal }),
    requestFetch<Overview>('/api/v1/statistics/overview', { query: { startDate: period.start, endDate: period.end }, signal }),
    requestFetch<CategoryStatistics>('/api/v1/statistics/categories', { query: { startDate: period.start, endDate: period.end, granularity: 'day' }, signal }),
  ])
  return { transactions: transactionData.items, overview, categoryStatistics }
}, { lazy: true })

const transactions = computed(() => data.value?.transactions || [])
const overview = computed(() => data.value?.overview || null)
const categoryStatistics = computed(() => data.value?.categoryStatistics || null)
const loadedData = computed(() => !!data.value)
const queryError = computed(() => error.value ? errorMessage(error.value) : '')
const cashFlow = ref<CashFlow | null>(null)
const cashFlowPending = ref(true)
const cashFlowError = ref('')
let cashFlowRequestId = 0
let cashFlowAbortController: AbortController | null = null
const cashFlowLoading = computed(() => cashFlowPending.value && !cashFlow.value && !cashFlowError.value)

const balance = computed(() => workspace.accounts.value.reduce((sum, account) => sum + minor(account.amount), 0))
const firstUse = computed(() => workspace.loaded.value && !workspace.accounts.value.length)
const categoryRows = computed(() => categoryStatistics.value?.topCategories || [])
const recentTransactions = computed(() => transactions.value.slice(0, 5))

const categoryColumns: TableColumn<CategoryStatistics['topCategories'][number]>[] = [
  { accessorKey: 'name', header: '分类' },
  { accessorKey: 'amountMinor', header: '金额' },
  { accessorKey: 'actions', header: '操作' },
]

const transactionColumns: TableColumn<Transaction>[] = [
  { accessorKey: 'transaction', header: '交易' },
  { accessorKey: 'occurredAt', header: '发生时间' },
  { accessorKey: 'amount', header: '金额' },
  { accessorKey: 'actions', header: '操作' },
]

function formatChange(value: number | null) {
  return value === null ? '上期为 0，暂无百分比' : `${value >= 0 ? '+' : ''}${value.toFixed(1)}% 较上期`
}

async function loadDashboard() {
  await Promise.allSettled([
    refresh({ dedupe: 'cancel' }),
    loadCashFlow(),
  ])
}

async function loadCashFlow() {
  const currentRequestId = ++cashFlowRequestId
  cashFlowAbortController?.abort()
  const controller = new AbortController()
  cashFlowAbortController = controller
  cashFlowPending.value = true
  cashFlowError.value = ''
  try {
    const data = await requestFetch<CashFlow>('/api/v1/statistics/cash-flow', {
      query: { startDate: period.start, endDate: period.end, granularity: 'day' },
      signal: controller.signal,
    })
    if (currentRequestId === cashFlowRequestId) cashFlow.value = data
  } catch (error) {
    if (currentRequestId === cashFlowRequestId && !controller.signal.aborted) cashFlowError.value = errorMessage(error)
  } finally {
    if (currentRequestId === cashFlowRequestId) {
      cashFlowPending.value = false
      cashFlowAbortController = null
    }
  }
}

function showCategoryTransactions(categoryId: string) {
  const state = defaultTransactionState(today)
  state.categoryId = categoryId
  return navigateTo({ path: '/transactions', query: serializeTransactionState(state, today) })
}

function showCashBucket(startAt: string, endAt: string) {
  const state = defaultTransactionState(today)
  state.start = localInput(startAt).slice(0, 10)
  state.end = localInput(endAt).slice(0, 10)
  return navigateTo({
    path: '/transactions',
    query: { ...serializeTransactionState(state, today), start: state.start, end: state.end },
  })
}

watch(workspace.refreshRevision, () => void loadDashboard())
onMounted(() => void loadCashFlow())
onBeforeUnmount(() => {
  cashFlowRequestId++
  cashFlowAbortController?.abort()
  cashFlowAbortController = null
})
</script>

<template>
  <div class="page-flow page-flow--overview" :aria-busy="loading">
    <UAlert
      v-if="queryError"
      color="error"
      variant="soft"
      icon="i-lucide-circle-alert"
      title="总览读取失败"
      :description="queryError"
      role="alert"
    >
      <template #actions>
        <UButton label="重试" color="error" variant="soft" :loading="loading" @click="loadDashboard" />
      </template>
    </UAlert>

    <UPageCard
      v-if="firstUse"
      icon="i-lucide-book-open-check"
      title="从第一笔开始建立你的账本"
      description="先创建账户，再用调账录入现有余额；添加收入和支出分类后即可开始记账。"
      variant="subtle"
      class="overview-welcome"
    >
      <template #footer>
        <div class="flex flex-wrap gap-2">
          <UButton label="创建第一个账户" icon="i-lucide-wallet-cards" @click="workspace.resourceEditor.value = { kind: 'accounts' }" />
          <UButton color="neutral" variant="outline" label="创建分类" icon="i-lucide-folder-plus" @click="workspace.resourceEditor.value = { kind: 'categories' }" />
        </div>
      </template>
    </UPageCard>

    <div v-else-if="loading && !loadedData" class="overview-loading" role="status" aria-label="正在读取当前账本状态">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-3"><USkeleton v-for="index in 3" :key="index" aria-hidden="true" class="h-32 w-full motion-reduce:animate-none" /></div>
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-[1.6fr_.9fr]"><USkeleton aria-hidden="true" class="h-72 w-full motion-reduce:animate-none" /><USkeleton aria-hidden="true" class="h-72 w-full motion-reduce:animate-none" /></div>
    </div>

    <template v-else-if="overview">
      <UCard variant="subtle" :ui="{ body: 'flex flex-wrap items-end justify-between gap-4 p-4 sm:p-5' }">
        <div><p class="m-0 text-sm text-muted">账户合计余额</p><strong class="mt-1 block text-3xl font-semibold tabular-nums text-highlighted">{{ money(balance) }}</strong></div>
        <UBadge color="neutral" variant="subtle">CNY · Asia/Shanghai</UBadge>
      </UCard>

      <section class="grid grid-cols-1 gap-4 md:grid-cols-3" aria-label="本期摘要">
        <MetricSummaryCard label="实际净现金流" :value="money(overview.netCashFlow.currentAmountMinor)" :comparison="formatChange(overview.netCashFlow.changePercent)" emphasis :icon="metricIcons.cashFlow" />
        <MetricSummaryCard label="本期普通收入" :value="money(overview.income.currentAmountMinor)" :comparison="formatChange(overview.income.changePercent)" icon="i-lucide-arrow-down-left" />
        <MetricSummaryCard label="消费净支出" :value="money(overview.netExpense.currentAmountMinor)" :comparison="formatChange(overview.netExpense.changePercent)" icon="i-lucide-arrow-up-right" />
      </section>

      <section class="grid min-w-0 grid-cols-1 gap-5 lg:grid-cols-[1.6fr_.9fr]" aria-label="总览工作区">
        <UCard class="min-w-0" variant="outline">
          <template #header><div class="flex items-start justify-between gap-4"><div><h2 class="m-0 text-base font-semibold text-highlighted">现金流趋势摘要</h2><p class="mt-1 text-xs text-muted">查看本月每日流入、流出和净额方向</p></div><NuxtLink class="text-sm text-primary hover:underline" to="/statistics">查看完整分析 →</NuxtLink></div></template>
          <div v-if="cashFlowLoading" class="cash-flow-loading" role="status" aria-label="正在读取现金流趋势">
            <div class="cash-flow-loading-grid" aria-hidden="true">
              <USkeleton v-for="index in 5" :key="index" class="cash-flow-loading-bar motion-reduce:animate-none" />
            </div>
          </div>
          <UAlert v-if="cashFlowError" class="mb-4" color="error" variant="soft" icon="i-lucide-circle-alert" title="现金流趋势读取失败" :description="cashFlowError" role="alert">
            <template #actions><UButton label="重试" color="error" variant="soft" :loading="cashFlowPending" @click="loadCashFlow" /></template>
          </UAlert>
          <LazyCashFlowTrend v-if="cashFlow" :buckets="cashFlow.buckets" granularity="day" variant="compact" @drilldown="showCashBucket" />
        </UCard>

        <UCard class="min-w-0" variant="outline">
          <template #header><div class="flex items-start justify-between gap-4"><div><h2 class="m-0 text-base font-semibold text-highlighted">支出分类排行</h2><p class="mt-1 text-xs text-muted">按本期消费净支出排序</p></div></div></template>
          <UEmpty v-if="!categoryRows.length" icon="i-lucide-folder-open" title="本期暂无消费" description="记录一笔支出后，这里会显示分类分布。" variant="subtle" />
          <UTable v-else :data="categoryRows" :columns="categoryColumns" caption="支出分类排行" :ui="{ td: 'align-middle' }">
            <template #name-cell="{ row }"><span class="font-medium text-highlighted">{{ row.original.name }}</span></template>
            <template #amountMinor-cell="{ row }"><strong class="tabular-nums">{{ money(row.original.amountMinor) }}</strong></template>
            <template #actions-cell="{ row }"><UButton color="neutral" variant="ghost" size="sm" label="查看流水" @click="showCategoryTransactions(row.original.categoryId)" /></template>
          </UTable>
        </UCard>

        <UCard class="min-w-0 lg:col-span-2" variant="outline">
          <template #header><div class="flex items-start justify-between gap-4"><div><h2 class="m-0 text-base font-semibold text-highlighted">近期流水</h2><p class="mt-1 text-xs text-muted">最近 5 笔有效交易</p></div><NuxtLink class="text-sm text-primary hover:underline" to="/transactions">查看全部流水 →</NuxtLink></div></template>
          <UEmpty v-if="!recentTransactions.length" icon="i-lucide-receipt-text" title="暂无交易" description="点击右上角“记一笔”开始记录。" variant="subtle" />
          <UTable v-else :data="recentTransactions" :columns="transactionColumns" caption="近期流水" :ui="{ td: 'align-middle' }">
            <template #transaction-cell="{ row }"><UButton color="neutral" variant="ghost" class="justify-start text-left" :aria-label="`查看详情：${row.original.description || kindLabels[row.original.type]}`" @click="workspace.openTransaction(row.original)"><span class="mr-2 rounded bg-elevated px-2 py-1 text-xs text-muted">{{ kindLabels[row.original.type] }}</span><span class="truncate">{{ row.original.description || kindLabels[row.original.type] }}</span></UButton></template>
            <template #occurredAt-cell="{ row }"><time class="whitespace-nowrap text-sm text-muted" :datetime="row.original.occurredAt">{{ localInput(row.original.occurredAt).replace('T', ' ') }}</time></template>
            <template #amount-cell="{ row }"><strong class="whitespace-nowrap tabular-nums" :class="row.original.type === 'expense' ? 'text-warning' : row.original.type === 'income' || row.original.type === 'expense_refund' ? 'text-success' : 'text-highlighted'">{{ signedAmount(row.original) }}</strong></template>
            <template #actions-cell="{ row }"><UButton color="neutral" variant="ghost" size="sm" label="详情" @click="workspace.openTransaction(row.original)" /></template>
          </UTable>
        </UCard>
      </section>
    </template>
  </div>
</template>

<style scoped>
.overview-loading {
  display: grid;
  gap: 20px;
}

.cash-flow-loading {
  min-width: 0;
  height: 190px;
}

.cash-flow-loading-grid {
  display: flex;
  align-items: end;
  justify-content: space-around;
  gap: 10px;
  height: 100%;
  padding: 24px 12px;
  border-radius: 10px;
  background: var(--ui-bg-muted);
}

.cash-flow-loading-bar {
  width: 9%;
  height: 45%;
}

.cash-flow-loading-bar:nth-child(2n) {
  height: 68%;
}
</style>
