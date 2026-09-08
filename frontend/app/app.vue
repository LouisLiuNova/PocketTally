<script setup lang="ts">
import { kindLabels, type Account, type Category, type ExpenseTransactionPage, type Granularity, type RefundSummary, type Tag, type Transaction } from '~/types/ledger'
import { errorMessage, type StatisticsQuery, type TransactionQuery } from '~/composables/useLedger'
import { localInput, minor, money } from '~/utils/money'

const ledger = useLedger()
const { accounts, categories, tags, transactions, transactionTotal, overview, cashFlow, expenses, categoryStatistics, tagStatistics, calendar, loading, loadError, loaded } = ledger
const navItems = [
  { label: '总览', icon: 'i-lucide-layout-dashboard' }, { label: '交易', icon: 'i-lucide-arrow-left-right' },
  { label: '账户', icon: 'i-lucide-wallet-cards' }, { label: '分类与标签', icon: 'i-lucide-shapes' },
  { label: '统计分析', icon: 'i-lucide-chart-no-axes-combined' },
]
const activeView = ref('总览')
const todayDate = localInput().slice(0, 10)
const today = new Intl.DateTimeFormat('zh-CN', { dateStyle: 'full', timeZone: 'Asia/Shanghai' }).format(new Date())
const txPage = ref(1)
const txStart = ref(todayDate.slice(0, 7) + '-01')
const txEnd = ref(shiftMonth(txStart.value, 1))
const search = ref('')
const typeFilter = ref('')
const accountFilter = ref('')
const categoryFilter = ref('')
const tagFilter = ref('')
const statusFilter = ref('active')
const statsPreset = ref('this_month')
const customStart = ref(txStart.value)
const customEnd = ref(txEnd.value)
const granularity = ref<Granularity>('day')
const calendarMonth = ref(todayDate.slice(0, 7))
const categoryParentId = ref('')
const queryError = ref('')
const notice = ref('')
const selected = ref<Transaction | null>(null)
const refundSummary = ref<RefundSummary | null>(null)
const refundLoading = ref(false)
const transactionEditor = ref<{ editing?: Transaction; refund?: Transaction; accountId?: string } | null>(null)
const resourceEditor = ref<{ kind: 'accounts' | 'categories' | 'tags'; item?: Account | Category | Tag } | null>(null)
const confirmation = ref<{ title: string; text: string; path: string; method: 'POST' | 'DELETE' } | null>(null)
const actionError = ref('')
const busy = ref(false)
const theme = ref('system')
const palette = ref('ruri')
const showAppearance = ref(false)
const drill = ref<{ title: string; data: ExpenseTransactionPage } | null>(null)
const drillLoading = ref(false)

function shiftMonth(dateValue: string, delta: number): string {
  const [year, month] = dateValue.slice(0, 7).split('-').map(Number)
  const value = new Date(Date.UTC(year, month - 1 + delta, 1))
  return `${value.getUTCFullYear()}-${String(value.getUTCMonth() + 1).padStart(2, '0')}-01`
}
function startOfYear(dateValue: string) { return `${dateValue.slice(0, 4)}-01-01` }
function nextDate(dateValue: string) {
  const [year, month, day] = dateValue.split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, day + 1)).toISOString().slice(0, 10)
}
const statisticsPeriod = computed(() => {
  const monthStart = todayDate.slice(0, 7) + '-01'
  if (statsPreset.value === 'last_month') return { startDate: shiftMonth(monthStart, -1), endDate: monthStart }
  if (statsPreset.value === 'year') return { startDate: startOfYear(todayDate), endDate: `${Number(todayDate.slice(0, 4)) + 1}-01-01` }
  if (statsPreset.value === 'twelve_months') return { startDate: shiftMonth(monthStart, -11), endDate: shiftMonth(monthStart, 1) }
  if (statsPreset.value === 'custom') return { startDate: customStart.value, endDate: customEnd.value }
  return { startDate: monthStart, endDate: shiftMonth(monthStart, 1) }
})
const transactionQuery = computed<TransactionQuery>(() => ({
  page: txPage.value, pageSize: 20,
  startAt: txStart.value ? new Date(`${txStart.value}T00:00:00+08:00`).toISOString() : undefined,
  endAt: txEnd.value ? new Date(`${txEnd.value}T00:00:00+08:00`).toISOString() : undefined,
  type: typeFilter.value || undefined, accountId: accountFilter.value || undefined,
  categoryId: categoryFilter.value || undefined, includeDescendants: !!categoryFilter.value,
  tagId: tagFilter.value || undefined, q: search.value.trim() || undefined, status: statusFilter.value,
}))
const statisticsQuery = computed<StatisticsQuery>(() => ({
  ...statisticsPeriod.value, granularity: granularity.value, month: calendarMonth.value,
  parentCategoryId: categoryParentId.value || undefined,
}))
const balance = computed(() => accounts.value.reduce((sum, account) => sum + minor(account.amount), 0))
const trendMax = computed(() => Math.max(1, ...(cashFlow.value?.buckets.flatMap(item => [item.incomeAmountMinor, item.expenseAmountMinor, Math.abs(item.netCashFlowMinor)]) || [1])))
const categoryMax = computed(() => Math.max(1, ...(categoryStatistics.value?.items.map(item => Math.abs(item.amountMinor)) || [1])))
const calendarMax = computed(() => Math.max(1, ...(calendar.value?.days.map(day => Math.abs(day.netCashFlowMinor)) || [1])))
const pageCount = computed(() => Math.max(1, Math.ceil(transactionTotal.value / 20)))

function formatChange(value: number | null) { return value === null ? '上期为 0，暂无百分比' : `${value >= 0 ? '+' : ''}${value.toFixed(1)}% 较上期` }
function bucketLabel(value: string) { return localInput(value).slice(0, 10) }
function accountNames(transaction: Transaction) { return [transaction.sourceAccount?.name, transaction.destinationAccount?.name].filter(Boolean).join(' → ') }
function signedAmount(transaction: Transaction) {
  const sign = transaction.type === 'income' || transaction.type === 'expense_refund' || (transaction.type === 'balance_adjustment' && transaction.balanceAdjustmentDirection === 'increase') ? '+' : transaction.type === 'transfer' ? '' : '−'
  return sign + money(minor(transaction.amount))
}
async function refreshAll() { await ledger.refresh(transactionQuery.value, statisticsQuery.value) }
async function refreshTransactions() {
  queryError.value = ''
  try { await ledger.loadTransactions(transactionQuery.value) } catch (error) { queryError.value = errorMessage(error) }
}
async function refreshStatistics() {
  queryError.value = ''
  if (statisticsPeriod.value.startDate >= statisticsPeriod.value.endDate) { queryError.value = '统计开始日期必须早于结束日期。'; return }
  try { await ledger.loadStatistics(statisticsQuery.value) } catch (error) { queryError.value = errorMessage(error) }
}
async function saved() {
  const selectedId = selected.value?.id
  transactionEditor.value = null; resourceEditor.value = null; notice.value = '已保存到本地账本'
  await refreshAll()
  if (selectedId) await openTransaction(selectedId)
}
async function openTransaction(transaction: Transaction | string) {
  queryError.value = ''; refundSummary.value = null; refundLoading.value = true
  try {
    selected.value = typeof transaction === 'string' ? await $fetch<Transaction>(`/api/v1/transactions/${transaction}`) : transaction
    if (selected.value.type === 'expense') refundSummary.value = await $fetch<RefundSummary>(`/api/v1/transactions/${selected.value.id}/refund-summary`)
  } catch (error) { queryError.value = errorMessage(error); selected.value = null }
  finally { refundLoading.value = false }
}
function deleteResource(kind: 'accounts' | 'categories' | 'tags', item: Account | Category | Tag) {
  actionError.value = ''; confirmation.value = { title: `删除「${item.name}」`, text: '仅未被引用的资源可以删除。有关联交易或子分类时，账本会保留资源并提示原因。', path: `/api/v1/${kind}/${item.id}`, method: 'DELETE' }
}
function voidSelected() {
  if (!selected.value) return
  actionError.value = ''; confirmation.value = { title: '作废这笔交易', text: '作废后撤销余额影响并保留审计记录。有有效退款的支出须先作废退款。', path: `/api/v1/transactions/${selected.value.id}/void`, method: 'POST' }
}
async function confirmAction() {
  if (!confirmation.value || busy.value) return
  busy.value = true; actionError.value = ''
  try {
    await $fetch(confirmation.value.path, { method: confirmation.value.method, retry: 0 })
    confirmation.value = null; notice.value = '操作成功'; await refreshAll()
    if (selected.value) await openTransaction(selected.value.id)
  } catch (error) { actionError.value = errorMessage(error) }
  finally { busy.value = false }
}
function showAccountLedger(accountId: string) { accountFilter.value = accountId; txPage.value = 1; activeView.value = '交易' }
function showCalendarDay(date: string) { txStart.value = date; txEnd.value = nextDate(date); activeView.value = '交易' }
function showCashBucket(startAt: string, endAt: string) { txStart.value = localInput(startAt).slice(0, 10); txEnd.value = localInput(endAt).slice(0, 10); txPage.value = 1; activeView.value = '交易' }
async function openExpenseDrill(title: string, query: Record<string, string | boolean>) {
  drillLoading.value = true; queryError.value = ''
  try {
    const data = await $fetch<ExpenseTransactionPage>('/api/v1/statistics/expense-transactions', { query: { ...statisticsPeriod.value, page: 1, pageSize: 100, ...query } })
    drill.value = { title, data }
  } catch (error) { queryError.value = errorMessage(error) }
  finally { drillLoading.value = false }
}
function applyAppearance() {
  document.documentElement.dataset.theme = theme.value === 'system' ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : theme.value
  document.documentElement.dataset.palette = palette.value
  try { localStorage.setItem('pockettally-appearance', JSON.stringify({ theme: theme.value, palette: palette.value })) } catch { /* 隐私模式仍允许切换外观。 */ }
}

let transactionTimer: ReturnType<typeof setTimeout> | undefined
watch([search, txStart, txEnd, typeFilter, accountFilter, categoryFilter, tagFilter, statusFilter], () => {
  txPage.value = 1; if (!loaded.value) return
  clearTimeout(transactionTimer); transactionTimer = setTimeout(() => void refreshTransactions(), 250)
})
watch(txPage, () => { if (loaded.value) void refreshTransactions() })
watch([statsPreset, customStart, customEnd, granularity, calendarMonth, categoryParentId], () => { if (loaded.value) void refreshStatistics() })
watch([theme, palette], () => { if (import.meta.client) applyAppearance() })
onMounted(() => {
  try { const savedAppearance = JSON.parse(localStorage.getItem('pockettally-appearance') || '{}'); theme.value = savedAppearance.theme || 'system'; palette.value = savedAppearance.palette || 'ruri' } catch { /* 忽略损坏的偏好。 */ }
  applyAppearance(); window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyAppearance); void refreshAll()
})
onBeforeUnmount(() => { clearTimeout(transactionTimer); window.matchMedia('(prefers-color-scheme: dark)').removeEventListener('change', applyAppearance) })
</script>

<template>
  <UApp>
    <div class="app-shell">
      <aside class="sidebar">
        <div class="brand"><div class="brand-mark"><UIcon name="i-lucide-circle-dollar-sign" /></div><span class="brand-label">PocketTally</span></div>
        <nav aria-label="主导航"><button v-for="item in navItems" :key="item.label" class="nav-item" :class="{ active: activeView === item.label }" :disabled="!loaded" :aria-label="item.label" @click="activeView = item.label"><UIcon :name="item.icon" /><span class="nav-label">{{ item.label }}</span></button></nav>
        <div class="sidebar-foot"><p class="hint">个人账本 · CNY<br>统计边界 · Asia/Shanghai</p></div>
      </aside>
      <main>
        <header class="topbar"><div><p class="eyebrow">{{ today }}</p><h1>{{ activeView === '总览' ? '我的账本' : activeView }}</h1></div><div class="top-actions"><UButton color="neutral" variant="ghost" icon="i-lucide-sun-moon" aria-label="外观设置" @click="showAppearance = !showAppearance" /><UButton color="neutral" variant="outline" label="刷新" :loading="loading" @click="refreshAll" /><UButton icon="i-lucide-plus" label="记一笔" :disabled="!loaded || loading || !!loadError" @click="transactionEditor = {}" /></div></header>
        <div v-if="showAppearance" class="view-toolbar"><label>主题 <select v-model="theme"><option value="system">跟随系统</option><option value="light">亮色</option><option value="dark">暗色</option></select></label><label>配色 <select v-model="palette"><option value="ruri">瑠璃浅葱</option><option value="toki">朱鷺色</option><option value="matsuba">松葉色</option><option value="fuji">藤紫</option></select></label></div>
        <p v-if="notice" role="status" class="info-strip">{{ notice }}<button class="text-link" aria-label="关闭提示" @click="notice = ''">×</button></p>
        <div v-if="loadError || queryError" role="alert" class="error-box">{{ loadError || queryError }} {{ loaded && loadError ? '以下为上次成功读取的数据。' : '' }}<UButton label="重试" color="neutral" @click="refreshAll" /></div>
        <p v-if="loading" role="status" class="empty-state">正在从账本服务同步分页流水与统计…</p>
        <template v-if="loaded">
          <section v-if="!accounts.length" class="panel welcome"><p class="eyebrow">从第一笔开始</p><h2>欢迎来到你的账本</h2><p>先创建账户，再用调账录入现有余额；添加收入和支出分类后即可开始记账。</p><UButton label="创建第一个账户" @click="resourceEditor = { kind: 'accounts' }" /><UButton color="neutral" variant="outline" label="创建分类" @click="resourceEditor = { kind: 'categories' }" /></section>

          <template v-if="activeView === '总览'">
            <section v-if="overview" class="metric-grid">
              <article class="metric-card feature"><span>实际净现金流</span><strong>{{ money(overview.netCashFlow.currentAmountMinor) }}</strong><p>{{ formatChange(overview.netCashFlow.changePercent) }}</p></article>
              <article class="metric-card"><span>本期普通收入</span><strong>{{ money(overview.income.currentAmountMinor) }}</strong><p>{{ formatChange(overview.income.changePercent) }}</p></article>
              <article class="metric-card"><span>消费净支出</span><strong>{{ money(overview.netExpense.currentAmountMinor) }}</strong><p>{{ formatChange(overview.netExpense.changePercent) }}</p></article>
            </section>
            <div class="dashboard-grid">
              <section class="panel"><div class="panel-head"><h2>现金流趋势</h2><span class="hint">退款按到账日计入流入</span></div><p v-if="!cashFlow?.buckets.length" class="empty-state">本期暂无现金流</p><div v-else class="real-trend"><div v-for="item in cashFlow.buckets" :key="item.startAt" class="trend-row"><span>{{ bucketLabel(item.startAt).slice(5) }}</span><div><div class="trend-track"><i :style="{ width: `${item.incomeAmountMinor / trendMax * 100}%` }" /></div><div class="trend-track expense-track"><i :style="{ width: `${item.expenseAmountMinor / trendMax * 100}%` }" /></div></div><small>收入 {{ money(item.incomeAmountMinor) }} · 退款 {{ money(item.refundAmountMinor) }} · 支出 {{ money(item.expenseAmountMinor) }} · 净额 {{ money(item.netCashFlowMinor) }}</small></div></div></section>
              <section class="panel"><h2>支出分类 Top 5</h2><p v-if="!categoryStatistics?.topCategories.length" class="empty-state">本期暂无消费</p><button v-for="item in categoryStatistics?.topCategories" :key="item.categoryId" class="resource-row drill-button" @click="openExpenseDrill(item.name, { categoryId: item.categoryId, includeDescendants: true })"><span>{{ item.name }}</span><strong>{{ money(item.amountMinor) }}</strong></button><div v-if="categoryStatistics?.other.amountMinor" class="resource-row"><span>其他</span><strong>{{ money(categoryStatistics.other.amountMinor) }}</strong></div></section>
              <section class="panel recent-panel"><div class="panel-head"><h2>近期流水</h2><button class="text-link" @click="activeView = '交易'">查看分页流水 →</button></div><p v-if="!transactions.length" class="empty-state">暂无交易，点击「记一笔」开始。</p><button v-for="transaction in transactions.slice(0, 5)" :key="transaction.id" class="mvp-transaction" @click="openTransaction(transaction)"><span class="transaction-icon blue">{{ kindLabels[transaction.type] }}</span><span><strong>{{ transaction.description || kindLabels[transaction.type] }}</strong><small>{{ transaction.category?.name || kindLabels[transaction.type] }} · {{ accountNames(transaction) }}</small></span><time>{{ localInput(transaction.occurredAt).replace('T', ' ') }}</time><b>{{ signedAmount(transaction) }}</b></button></section>
            </div>
          </template>

          <section v-if="activeView === '交易'">
            <div class="view-toolbar wrap transaction-filters">
              <input v-model="search" class="search-field" aria-label="搜索交易" placeholder="搜索说明、分类、账户或标签">
              <label>开始日期<input v-model="txStart" type="date"></label><label>结束日期（不含）<input v-model="txEnd" type="date"></label>
              <select v-model="typeFilter" aria-label="交易类型筛选"><option value="">所有类型</option><option v-for="(label, kind) in kindLabels" :key="kind" :value="kind">{{ label }}</option></select>
              <select v-model="accountFilter" aria-label="账户筛选"><option value="">所有账户</option><option v-for="account in accounts" :key="account.id" :value="account.id">{{ account.name }}</option></select>
              <select v-model="categoryFilter" aria-label="分类筛选"><option value="">所有分类</option><option v-for="category in categories" :key="category.id" :value="category.id">{{ category.name }}</option></select>
              <select v-model="tagFilter" aria-label="标签筛选"><option value="">所有标签</option><option v-for="tag in tags" :key="tag.id" :value="tag.id">{{ tag.name }}</option></select>
              <select v-model="statusFilter" aria-label="状态筛选"><option value="active">仅有效</option><option value="voided">仅作废</option><option value="all">全部状态</option></select>
            </div>
            <section class="panel"><div class="panel-head"><h2>交易记录</h2><span class="hint">服务端共 {{ transactionTotal }} 笔</span></div><p v-if="!transactions.length" class="empty-state">没有符合条件的交易</p><button v-for="transaction in transactions" :key="transaction.id" class="mvp-transaction" :class="{ voided: transaction.isVoid }" @click="openTransaction(transaction)"><span class="transaction-icon blue">{{ kindLabels[transaction.type] }}</span><span><strong>{{ transaction.description || kindLabels[transaction.type] }} {{ transaction.isVoid ? '（已作废）' : '' }}</strong><small>{{ transaction.category?.name }} · {{ accountNames(transaction) }} <span v-for="tag in transaction.tags" :key="tag.id" class="tag">{{ tag.name }}</span></small></span><time>{{ localInput(transaction.occurredAt).replace('T', ' ') }}</time><b>{{ signedAmount(transaction) }}</b></button><div v-if="transactionTotal > 20" class="pagination"><UButton label="上一页" color="neutral" :disabled="txPage <= 1" @click="txPage--" /><span>{{ txPage }} / {{ pageCount }}</span><UButton label="下一页" color="neutral" :disabled="txPage >= pageCount" @click="txPage++" /></div></section>
          </section>

          <section v-if="activeView === '账户'">
            <div class="section-intro"><div><p>账户合计余额</p><h2>{{ money(balance) }}</h2></div><UButton label="新建账户" icon="i-lucide-plus" @click="resourceEditor = { kind: 'accounts' }" /></div>
            <div class="account-card-grid"><article v-for="account in accounts" :key="account.id" class="balance-card"><span>{{ account.type === 'debit' ? '借记账户' : '信用账户' }}</span><div class="card-brand">{{ account.name }}</div><strong>{{ money(minor(account.amount)) }}</strong><small>{{ account.description || account.cardNumber || '余额来自有效交易' }}</small><div><button @click="transactionEditor = { accountId: account.id }">调账</button><button @click="showAccountLedger(account.id)">流水</button><button @click="resourceEditor = { kind: 'accounts', item: account }">编辑</button><button class="danger" @click="deleteResource('accounts', account)">删除</button></div></article></div>
          </section>

          <section v-if="activeView === '分类与标签'" class="taxonomy-grid">
            <article class="panel"><div class="panel-head"><h2>分类</h2><UButton label="新建分类" @click="resourceEditor = { kind: 'categories' }" /></div><p v-if="!categories.length" class="empty-state">创建收入、支出分类，让每笔收支有归属。</p><div v-for="category in categories" :key="category.id" class="resource-row"><span><i class="color-dot" :style="{ background: category.iconColor }" /><strong>{{ category.name }}</strong><small>{{ category.purpose === 'income' ? '收入' : '支出' }} · {{ category.parentCategory ? `上级：${category.parentCategory.name}` : '顶级分类' }}</small></span><div><button class="text-link" @click="resourceEditor = { kind: 'categories', item: category }">编辑</button><button class="text-link danger" @click="deleteResource('categories', category)">删除</button></div></div></article>
            <article class="panel"><div class="panel-head"><h2>标签</h2><UButton label="新建标签" @click="resourceEditor = { kind: 'tags' }" /></div><p v-if="!tags.length" class="empty-state">标签可选，用来标记项目、旅行或其他用途。</p><div v-for="tag in tags" :key="tag.id" class="resource-row"><span><i class="color-dot" :style="{ background: tag.color }" />{{ tag.name }}</span><div><button class="text-link" @click="resourceEditor = { kind: 'tags', item: tag }">编辑</button><button class="text-link danger" @click="deleteResource('tags', tag)">删除</button></div></div></article>
          </section>

          <section v-if="activeView === '统计分析'">
            <div class="view-toolbar wrap analytics-toolbar"><div class="period-tabs"><button v-for="item in [{v:'this_month',l:'本月'},{v:'last_month',l:'上月'},{v:'year',l:'今年'},{v:'twelve_months',l:'近 12 个月'},{v:'custom',l:'自定义'}]" :key="item.v" :class="{ active: statsPreset === item.v }" @click="statsPreset = item.v">{{ item.l }}</button></div><template v-if="statsPreset === 'custom'"><label>开始<input v-model="customStart" type="date"></label><label>结束（不含）<input v-model="customEnd" type="date"></label></template><label>粒度<select v-model="granularity"><option value="day">日</option><option value="week">周</option><option value="month">月</option></select></label></div>
            <section v-if="overview" class="metric-grid"><article class="metric-card feature"><span>实际净现金流</span><strong>{{ money(overview.netCashFlow.currentAmountMinor) }}</strong><p>{{ formatChange(overview.netCashFlow.changePercent) }}</p></article><article class="metric-card"><span>普通收入</span><strong>{{ money(overview.income.currentAmountMinor) }}</strong><p>{{ formatChange(overview.income.changePercent) }}</p></article><article class="metric-card"><span>消费净支出</span><strong>{{ money(overview.netExpense.currentAmountMinor) }}</strong><p>{{ formatChange(overview.netExpense.changePercent) }}</p></article></section>
            <div class="analytics-grid">
              <section class="panel"><div class="panel-head"><h2>现金流趋势</h2><span class="hint">点击时间桶查看流水</span></div><div class="real-trend"><button v-for="item in cashFlow?.buckets" :key="item.startAt" class="trend-row bucket-button" @click="showCashBucket(item.startAt, item.endAt)"><span>{{ bucketLabel(item.startAt).slice(5) }}</span><div><div class="trend-track"><i :style="{ width: `${item.incomeAmountMinor / trendMax * 100}%` }" /></div><div class="trend-track expense-track"><i :style="{ width: `${item.expenseAmountMinor / trendMax * 100}%` }" /></div></div><small>{{ money(item.incomeAmountMinor) }} / 退款 {{ money(item.refundAmountMinor) }} / 支出 {{ money(item.expenseAmountMinor) }} / 净额 {{ money(item.netCashFlowMinor) }}</small></button></div></section>
              <section class="panel"><div class="panel-head"><h2>消费趋势</h2><span class="hint">点击时间桶查看净额明细</span></div><p v-if="!expenses?.buckets.length" class="empty-state">本期暂无消费</p><button v-for="item in expenses?.buckets" :key="item.startAt" class="resource-row drill-button" @click="openExpenseDrill(bucketLabel(item.startAt), { startDate: bucketLabel(item.startAt), endDate: bucketLabel(item.endAt) })"><span>{{ bucketLabel(item.startAt) }}</span><span>{{ money(item.netExpenseMinor) }} / 累计 {{ money(item.cumulativeNetExpenseMinor) }}</span></button></section>
              <section class="panel"><div class="panel-head"><h2>分类分析</h2><button v-if="categoryParentId" class="text-link" @click="categoryParentId = ''">返回一级分类</button></div><p class="hint">退款按原支出日期抵减；点击分类查看净额明细。</p><button v-for="item in categoryStatistics?.items" :key="item.categoryId" class="category-stat" @click="openExpenseDrill(item.name, { categoryId: item.categoryId, includeDescendants: true })"><span><strong>{{ item.name }}</strong><small>直接 {{ money(item.directAmountMinor) }} · 变化贡献 {{ money(item.changeContributionMinor) }}</small></span><i :style="{ width: `${Math.abs(item.amountMinor) / categoryMax * 100}%` }" /><b>{{ money(item.amountMinor) }}</b></button><div v-for="parent in categoryStatistics?.items.filter(item => item.children.length)" :key="`${parent.categoryId}-children`" class="child-links"><span>{{ parent.name }} 下钻：</span><button v-for="child in parent.children" :key="child.categoryId" @click="openExpenseDrill(`${parent.name} / ${child.name}`, { categoryId: child.categoryId, includeDescendants: true })">{{ child.name }} {{ money(child.amountMinor) }}</button></div></section>
              <section class="panel"><h2>Tag 汇总</h2><p class="hint">一笔交易可完整计入多个 Tag，因此不提供 Tag 合计或占比。</p><button v-for="item in tagStatistics?.items" :key="item.tagId" class="resource-row drill-button" @click="openExpenseDrill(`Tag：${item.name}`, { tagId: item.tagId })"><span><i class="color-dot" :style="{ background: item.color }" />{{ item.name }}</span><strong>{{ money(item.netExpenseMinor) }}</strong></button></section>
              <section class="panel calendar-panel"><div class="panel-head"><div><h2>收支日历</h2><p class="hint">点击日期查看服务端筛选的当日流水</p></div><label>月份 <input v-model="calendarMonth" type="month"></label></div><div class="calendar-grid"><button v-for="day in calendar?.days" :key="day.date" :style="{ '--heat': `${Math.abs(day.netCashFlowMinor) / calendarMax * 18}%` }" @click="showCalendarDay(day.date)"><b>{{ day.date.slice(-2) }}</b><span>{{ money(day.netCashFlowMinor) }}</span><small>入 {{ money(day.incomeAmountMinor + day.refundAmountMinor) }} / 出 {{ money(day.expenseAmountMinor) }}</small></button></div></section>
            </div>
            <section v-if="drill || drillLoading" class="panel drill-panel"><div class="panel-head"><h2>{{ drill?.title || '正在读取明细…' }}</h2><button class="text-link" @click="drill = null">关闭</button></div><template v-if="drill"><p class="hint">原支出 {{ money(drill.data.totals.originalAmountMinor) }} − 有效退款 {{ money(drill.data.totals.refundedAmountMinor) }} = 净支出 {{ money(drill.data.totals.netExpenseMinor) }}；共 {{ drill.data.total }} 笔。</p><button v-for="item in drill.data.items" :key="item.transaction.id" class="mvp-transaction" @click="openTransaction(item.transaction.id)"><span class="transaction-icon blue">支出</span><span><strong>{{ item.transaction.description || '支出' }}</strong><small>原支出 {{ money(item.originalAmountMinor) }} · 已退 {{ money(item.refundedAmountMinor) }}</small></span><time>{{ localInput(item.transaction.occurredAt).replace('T', ' ') }}</time><b>{{ money(item.netExpenseMinor) }}</b></button></template></section>
          </section>
        </template>
      </main>
    </div>

    <UModal :open="!!transactionEditor" :dismissible="false" title="交易表单" @update:open="value => { if (!value) transactionEditor = null }"><template #content><TransactionEditor v-if="transactionEditor" v-bind="transactionEditor" :accounts="accounts" :categories="categories" :tags="tags" :refund-summary="refundSummary" @close="transactionEditor = null" @saved="saved" /></template></UModal>
    <UModal :open="!!resourceEditor" :dismissible="false" title="资源表单" @update:open="value => { if (!value) resourceEditor = null }"><template #content><ResourceEditor v-if="resourceEditor" v-bind="resourceEditor" :categories="categories" @close="resourceEditor = null" @saved="saved" /></template></UModal>
    <UModal :open="!!selected && !transactionEditor && !confirmation" title="交易详情" @update:open="value => { if (!value) selected = null }"><template #body><template v-if="selected"><div class="detail-amount">{{ signedAmount(selected) }}<span class="status-dot">{{ selected.isVoid ? '已作废' : '有效' }}</span></div><dl class="mvp-detail"><dt>类型</dt><dd>{{ kindLabels[selected.type] }}</dd><dt>说明</dt><dd>{{ selected.description || '无' }}</dd><dt>账户</dt><dd>{{ accountNames(selected) }}</dd><dt>分类</dt><dd>{{ selected.category?.name || '不适用' }}</dd><dt>发生时间</dt><dd>{{ localInput(selected.occurredAt).replace('T', ' ') }}（上海）</dd><dt>标签</dt><dd>{{ selected.tags.map(tag => tag.name).join('、') || '无' }}</dd><template v-if="selected.voidedAt"><dt>作废时间</dt><dd>{{ localInput(selected.voidedAt).replace('T', ' ') }}</dd></template></dl><p v-if="selected.type === 'expense'" class="info-strip">{{ refundLoading ? '正在读取退款额度…' : `已退 ${money(refundSummary?.refundedAmountMinor || 0)} · 剩余可退 ${money(refundSummary?.remainingRefundableAmountMinor || 0)}` }}</p><button v-if="selected.refundOfTransactionId" class="text-link" @click="openTransaction(selected.refundOfTransactionId)">查看原支出 →</button><div v-if="!selected.isVoid" class="composer-actions"><UButton label="编辑交易" color="neutral" @click="transactionEditor = { editing: selected }" /><UButton v-if="selected.type === 'expense'" label="申请退款" :disabled="refundLoading || !refundSummary?.canRefund" @click="transactionEditor = { refund: selected }" /><UButton label="作废交易" color="error" variant="soft" @click="voidSelected" /></div></template></template></UModal>
    <UModal :open="!!confirmation" :dismissible="!busy" :title="confirmation?.title" @update:open="value => { if (!value && !busy) confirmation = null }"><template #body><p>{{ confirmation?.text }}</p><p v-if="actionError" role="alert" class="error-box">{{ actionError }}</p></template><template #footer><UButton label="取消" color="neutral" :disabled="busy" @click="confirmation = null" /><UButton label="确认操作" color="error" :loading="busy" :disabled="busy" @click="confirmAction" /></template></UModal>
  </UApp>
</template>
