<script setup lang="ts">
import { kindLabels, type CashFlow, type CategoryStatistics, type Overview, type Page, type Transaction } from '~/types/ledger'
import { errorMessage, type TransactionQuery } from '~/composables/useLedger'
import { defaultTransactionState, monthPeriod, serializeTransactionState } from '~/utils/routeQuery'
import { localInput, minor, money } from '~/utils/money'
import { accountNames, signedAmount } from '~/utils/transactionDisplay'

const workspace = useLedgerWorkspace()
const today = localInput().slice(0, 10)
const transactions = ref<Transaction[]>([])
const overview = ref<Overview | null>(null)
const cashFlow = ref<CashFlow | null>(null)
const categoryStatistics = ref<CategoryStatistics | null>(null)
const loading = ref(false)
const queryError = ref('')
let requestId = 0

const balance = computed(() => workspace.accounts.value.reduce((sum, account) => sum + minor(account.amount), 0))
const trendMax = computed(() => Math.max(1, ...(cashFlow.value?.buckets.flatMap(item => [item.incomeAmountMinor, item.expenseAmountMinor, Math.abs(item.netCashFlowMinor)]) || [1])))

function formatChange(value: number | null) {
  return value === null ? '上期为 0，暂无百分比' : `${value >= 0 ? '+' : ''}${value.toFixed(1)}% 较上期`
}

function bucketLabel(value: string) {
  return localInput(value).slice(0, 10)
}

async function loadDashboard() {
  const currentRequest = ++requestId
  const period = monthPeriod(today)
  const transactionQuery: TransactionQuery = {
    page: 1,
    pageSize: 20,
    startAt: new Date(`${period.start}T00:00:00+08:00`).toISOString(),
    endAt: new Date(`${period.end}T00:00:00+08:00`).toISOString(),
    status: 'active',
  }
  loading.value = true
  queryError.value = ''
  try {
    const [transactionData, overviewData, flowData, categoryData] = await Promise.all([
      $fetch<Page<Transaction>>('/api/v1/transactions', { query: transactionQuery }),
      $fetch<Overview>('/api/v1/statistics/overview', { query: { startDate: period.start, endDate: period.end } }),
      $fetch<CashFlow>('/api/v1/statistics/cash-flow', { query: { startDate: period.start, endDate: period.end, granularity: 'day' } }),
      $fetch<CategoryStatistics>('/api/v1/statistics/categories', { query: { startDate: period.start, endDate: period.end, granularity: 'day' } }),
    ])
    if (currentRequest !== requestId) return
    transactions.value = transactionData.items
    overview.value = overviewData
    cashFlow.value = flowData
    categoryStatistics.value = categoryData
  } catch (error) {
    if (currentRequest === requestId) queryError.value = errorMessage(error)
  } finally {
    if (currentRequest === requestId) loading.value = false
  }
}

function showCategoryTransactions(categoryId: string) {
  const state = defaultTransactionState(today)
  state.categoryId = categoryId
  return navigateTo({ path: '/transactions', query: serializeTransactionState(state, today) })
}

onMounted(() => void loadDashboard())
watch(workspace.refreshRevision, () => void loadDashboard())
onBeforeUnmount(() => { requestId++ })
</script>

<template>
  <section v-if="workspace.loaded.value && !workspace.accounts.value.length" class="panel welcome">
    <p class="eyebrow">从第一笔开始</p><h2>欢迎来到你的账本</h2>
    <p>先创建账户，再用调账录入现有余额；添加收入和支出分类后即可开始记账。</p>
    <UButton label="创建第一个账户" @click="workspace.resourceEditor.value = { kind: 'accounts' }" />
    <UButton color="neutral" variant="outline" label="创建分类" @click="workspace.resourceEditor.value = { kind: 'categories' }" />
  </section>
  <div v-if="queryError" role="alert" class="error-box">{{ queryError }}<UButton label="重试" color="neutral" @click="loadDashboard" /></div>
  <p v-if="loading && !overview" role="status" class="empty-state">正在读取当前账本状态…</p>

  <template v-if="overview">
    <div class="section-intro">
      <div><p>账户合计余额</p><h2>{{ money(balance) }}</h2></div>
    </div>
    <section class="metric-grid">
      <article class="metric-card feature"><span>实际净现金流</span><strong>{{ money(overview.netCashFlow.currentAmountMinor) }}</strong><p>{{ formatChange(overview.netCashFlow.changePercent) }}</p></article>
      <article class="metric-card"><span>本期普通收入</span><strong>{{ money(overview.income.currentAmountMinor) }}</strong><p>{{ formatChange(overview.income.changePercent) }}</p></article>
      <article class="metric-card"><span>消费净支出</span><strong>{{ money(overview.netExpense.currentAmountMinor) }}</strong><p>{{ formatChange(overview.netExpense.changePercent) }}</p></article>
    </section>
    <div class="dashboard-grid">
      <section class="panel">
        <div class="panel-head"><h2>现金流趋势摘要</h2><NuxtLink class="text-link" to="/statistics">查看完整分析 →</NuxtLink></div>
        <p v-if="!cashFlow?.buckets.length" class="empty-state">本期暂无现金流</p>
        <div v-else class="real-trend" tabindex="0" aria-label="现金流趋势摘要数据">
          <div v-for="item in cashFlow.buckets" :key="item.startAt" class="trend-row">
            <span>{{ bucketLabel(item.startAt).slice(5) }}</span>
            <div><div class="trend-track"><i :style="{ width: `${item.incomeAmountMinor / trendMax * 100}%` }" /></div><div class="trend-track expense-track"><i :style="{ width: `${item.expenseAmountMinor / trendMax * 100}%` }" /></div></div>
            <small>收入 {{ money(item.incomeAmountMinor) }} · 退款 {{ money(item.refundAmountMinor) }} · 支出 {{ money(item.expenseAmountMinor) }} · 净额 {{ money(item.netCashFlowMinor) }}</small>
          </div>
        </div>
      </section>
      <section class="panel">
        <h2>支出分类 Top 5</h2>
        <p v-if="!categoryStatistics?.topCategories.length" class="empty-state">本期暂无消费</p>
        <button v-for="item in categoryStatistics?.topCategories" :key="item.categoryId" class="resource-row drill-button" @click="showCategoryTransactions(item.categoryId)"><span>{{ item.name }}</span><strong>{{ money(item.amountMinor) }}</strong></button>
        <div v-if="categoryStatistics?.other.amountMinor" class="resource-row"><span>其他</span><strong>{{ money(categoryStatistics.other.amountMinor) }}</strong></div>
      </section>
      <section class="panel recent-panel">
        <div class="panel-head"><h2>近期流水</h2><NuxtLink class="text-link" to="/transactions">查看分页流水 →</NuxtLink></div>
        <p v-if="!transactions.length" class="empty-state">暂无交易，点击「记一笔」开始。</p>
        <button v-for="transaction in transactions.slice(0, 5)" :key="transaction.id" class="mvp-transaction" @click="workspace.openTransaction(transaction)">
          <span class="transaction-icon blue">{{ kindLabels[transaction.type] }}</span>
          <span><strong>{{ transaction.description || kindLabels[transaction.type] }}</strong><small>{{ transaction.category?.name || kindLabels[transaction.type] }} · {{ accountNames(transaction) }}</small></span>
          <time>{{ localInput(transaction.occurredAt).replace('T', ' ') }}</time><b>{{ signedAmount(transaction) }}</b>
        </button>
      </section>
    </div>
  </template>
</template>
