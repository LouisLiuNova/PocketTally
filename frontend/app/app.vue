<script setup lang="ts">
import { kindLabels, type Transaction, type Account, type Category, type Tag } from '~/types/ledger'
import { minor, money, localInput } from '~/utils/money'
import { summarize } from '~/utils/reports'
import { errorMessage } from '~/composables/useLedger'
const { accounts, categories, tags, transactions, loading, loadError, loaded, refresh } = useLedger()
const navItems = [
  { label: '总览', icon: 'i-lucide-layout-dashboard' }, { label: '交易', icon: 'i-lucide-arrow-left-right' },
  { label: '账户', icon: 'i-lucide-wallet-cards' }, { label: '分类与标签', icon: 'i-lucide-shapes' },
  { label: '统计分析', icon: 'i-lucide-chart-no-axes-combined' },
]
const activeView = ref('总览')
const month = ref(localInput().slice(0, 7))
const search = ref('')
const typeFilter = ref('')
const accountFilter = ref('')
const includeVoided = ref(false)
const notice = ref('')
const selectedId = ref('')
const selected = computed(() => transactions.value.find(t => t.id === selectedId.value))
const transactionEditor = ref<{ editing?: Transaction; refund?: Transaction; accountId?: string } | null>(null)
const resourceEditor = ref<{ kind: 'accounts' | 'categories' | 'tags'; item?: Account | Category | Tag } | null>(null)
const confirmation = ref<{ title: string; text: string; path: string; method: 'POST' | 'DELETE' } | null>(null)
const busy = ref(false)
const actionError = ref('')
const theme = ref('system')
const palette = ref('ruri')
const showAppearance = ref(false)
const page = ref(1)
const today = new Intl.DateTimeFormat('zh-CN', { dateStyle: 'full' }).format(new Date())
const monthTransactions = computed(() => transactions.value.filter(t => !t.isVoid && (!month.value || localInput(t.occurredAt).startsWith(month.value))))
const totals = computed(() => summarize(monthTransactions.value))
const balance = computed(() => accounts.value.reduce((sum, a) => sum + minor(a.amount), 0))
const filtered = computed(() => transactions.value.filter(t => {
  const words = [t.description, t.category?.name, t.sourceAccount?.name, t.destinationAccount?.name, ...t.tags.map(tag => tag.name)].join(' ').toLowerCase()
  return (includeVoided.value || !t.isVoid) && (!month.value || localInput(t.occurredAt).startsWith(month.value)) && (!typeFilter.value || typeFilter.value === t.type) && (!accountFilter.value || [t.sourceAccount?.id, t.destinationAccount?.id].includes(accountFilter.value)) && words.includes(search.value.toLowerCase().trim())
}).sort((a, b) => Date.parse(b.occurredAt) - Date.parse(a.occurredAt)))
const rows = computed(() => filtered.value.slice((page.value - 1) * 20, page.value * 20))
watch([search, month, typeFilter, accountFilter, includeVoided], () => { page.value = 1 })
const categoryStats = computed(() => {
  const values = new Map<string, number>()
  for (const t of monthTransactions.value) {
    if (t.type !== 'expense' && t.type !== 'expense_refund') continue
    const name = t.category?.name || '未分类'
    values.set(name, (values.get(name) || 0) + minor(t.amount) * (t.type === 'expense' ? 1 : -1))
  }
  return [...values].map(([name, amount]) => ({ name, amount })).sort((a, b) => b.amount - a.amount)
})
const trend = computed(() => {
  const values = new Map<string, { income: number; expense: number }>()
  for (const t of monthTransactions.value) {
    if (!['income', 'expense', 'expense_refund'].includes(t.type)) continue
    const day = localInput(t.occurredAt).slice(0, 10)
    const row = values.get(day) || { income: 0, expense: 0 }
    if (t.type === 'income') row.income += minor(t.amount)
    else row.expense += minor(t.amount) * (t.type === 'expense_refund' ? -1 : 1)
    values.set(day, row)
  }
  return [...values].sort(([a], [b]) => a.localeCompare(b)).map(([day, amounts]) => ({ day, ...amounts }))
})
const trendMax = computed(() => Math.max(1, ...trend.value.flatMap(t => [t.income, Math.abs(t.expense)])))
const refundTotal = computed(() => selected.value ? transactions.value.filter(t => !t.isVoid && t.refundOfTransactionId === selected.value!.id).reduce((sum, t) => sum + minor(t.amount), 0) : 0)
function accountNames(t: Transaction) { return [t.sourceAccount?.name, t.destinationAccount?.name].filter(Boolean).join(' → ') }
function signedAmount(t: Transaction) {
  const sign = t.type === 'income' || t.type === 'expense_refund' || (t.type === 'balance_adjustment' && t.balanceAdjustmentDirection === 'increase') ? '+' : t.type === 'transfer' ? '' : '−'
  return sign + money(minor(t.amount))
}
async function saved() {
  transactionEditor.value = null; resourceEditor.value = null
  notice.value = '已保存到本地账本'; await refresh()
}
function deleteResource(kind: 'accounts' | 'categories' | 'tags', item: Account | Category | Tag) {
  actionError.value = ''; confirmation.value = { title: `删除「${item.name}」`, text: '仅未被引用的资源可以删除。有关联交易或子分类时，账本会保留资源并提示原因。', path: `/api/v1/${kind}/${item.id}`, method: 'DELETE' }
}
function voidSelected() {
  if (!selected.value) return
  actionError.value = ''; confirmation.value = { title: '作废这笔交易', text: '作废后将撤销余额影响，保留审计记录且不可恢复。有有效退款的支出须先作废退款。', path: `/api/v1/transactions/${selected.value.id}/void`, method: 'POST' }
}
async function confirmAction() {
  if (!confirmation.value || busy.value) return
  busy.value = true; actionError.value = ''
  try {
    await $fetch(confirmation.value.path, { method: confirmation.value.method, retry: 0 })
    confirmation.value = null; notice.value = '操作成功'; await refresh()
  } catch (e) { actionError.value = errorMessage(e) }
  finally { busy.value = false }
}
function applyAppearance() {
  document.documentElement.dataset.theme = theme.value === 'system' ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : theme.value
  document.documentElement.dataset.palette = palette.value
  try { localStorage.setItem('pockettally-appearance', JSON.stringify({ theme: theme.value, palette: palette.value })) } catch { /* 隐私模式仍允许切换外观。 */ }
}
watch([theme, palette], () => { if (import.meta.client) applyAppearance() })
onMounted(() => {
  try { const saved = JSON.parse(localStorage.getItem('pockettally-appearance') || '{}'); theme.value = saved.theme || 'system'; palette.value = saved.palette || 'ruri' } catch { /* 忽略损坏的偏好。 */ }
  applyAppearance(); window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyAppearance)
  void refresh()
})
onBeforeUnmount(() => window.matchMedia('(prefers-color-scheme: dark)').removeEventListener('change', applyAppearance))
</script>

<template>
  <UApp>
    <div class="app-shell">
      <aside class="sidebar">
        <div class="brand"><div class="brand-mark"><UIcon name="i-lucide-circle-dollar-sign" /></div><span class="brand-label">PocketTally</span></div>
        <nav aria-label="主导航"><button v-for="item in navItems" :key="item.label" class="nav-item" :class="{ active: activeView === item.label }" :disabled="!loaded" :title="item.label" :aria-label="item.label" @click="activeView = item.label"><UIcon :name="item.icon" /><span class="nav-label">{{ item.label }}</span></button></nav>
        <div class="sidebar-foot"><p class="hint">个人账本 · CNY<br>每一笔，都有迹可循</p></div>
      </aside>
      <main>
        <header class="topbar"><div><p class="eyebrow">{{ today }}</p><h1>{{ activeView === '总览' ? '我的账本' : activeView }}</h1></div><div class="top-actions"><UButton color="neutral" variant="ghost" icon="i-lucide-sun-moon" aria-label="外观设置" @click="showAppearance = !showAppearance" /><UButton color="neutral" variant="outline" label="刷新" :loading="loading" @click="refresh" /><UButton icon="i-lucide-plus" label="记一笔" :disabled="!loaded || loading || !!loadError" @click="transactionEditor = {}" /></div></header>
        <div v-if="showAppearance" class="view-toolbar"><label>主题 <select v-model="theme"><option value="system">跟随系统</option><option value="light">亮色</option><option value="dark">暗色</option></select></label><label>配色 <select v-model="palette"><option value="ruri">瑠璃浅葱</option><option value="toki">朱鷺色</option><option value="matsuba">松葉色</option><option value="fuji">藤紫</option></select></label></div>
        <p v-if="notice" role="status" class="info-strip">{{ notice }}<button class="text-link" aria-label="关闭提示" @click="notice = ''">×</button></p>
        <div v-if="loadError" role="alert" class="error-box">{{ loadError }} {{ loaded ? '以下为上次成功读取的数据。' : '' }}<UButton label="重试" color="neutral" @click="refresh" /></div>
        <p v-if="loading" role="status" class="empty-state">正在同步账本…</p>
        <template v-if="loaded">
          <section v-if="!accounts.length" class="panel welcome"><p class="eyebrow">从第一笔开始</p><h2>欢迎来到你的账本</h2><p>先创建账户，再用调账录入现有余额；添加收入和支出分类后即可开始记账。</p><UButton label="创建第一个账户" @click="resourceEditor = { kind: 'accounts' }" /><UButton color="neutral" variant="outline" label="创建分类" @click="resourceEditor = { kind: 'categories' }" /></section>
          <div v-if="['总览', '交易', '统计分析'].includes(activeView)" class="view-toolbar"><label>统计月份 <input v-model="month" type="month" aria-label="统计月份"></label><button class="filter-chip" @click="month = ''">全部时间</button><button class="filter-chip" @click="month = localInput().slice(0, 7)">本月</button></div>
          <section v-if="activeView === '总览' || activeView === '统计分析'" class="metric-grid">
            <article class="metric-card feature"><span>净收支</span><strong>{{ money(totals.income - totals.net) }}</strong><p>收入 − 净支出</p></article>
            <article class="metric-card"><span>{{ month || '全部时间' }}收入</span><strong>{{ money(totals.income) }}</strong><p>仅普通收入</p></article>
            <article class="metric-card"><span>消费净支出</span><strong>{{ money(totals.net) }}</strong><p>支出 {{ money(totals.expense) }} − 退款 {{ money(totals.refunds) }}</p></article>
          </section>
          <template v-if="activeView === '总览' || activeView === '统计分析'">
            <div class="dashboard-grid">
              <section class="panel"><div class="panel-head"><h2>收支节奏</h2><span class="hint">按发生日期</span></div><p v-if="!trend.length" class="empty-state">本期还没有收支记录</p><div v-else class="real-trend"><div v-for="day in trend" :key="day.day" class="trend-row"><span>{{ day.day.slice(5) }}</span><div><div class="trend-track"><i :style="{ width: `${day.income / trendMax * 100}%` }" /></div><div class="trend-track expense-track"><i :style="{ width: `${Math.abs(day.expense) / trendMax * 100}%` }" /></div></div><small>收入 {{ money(day.income) }} / 净支出 {{ money(day.expense) }}</small></div></div><p class="hint">退款按到账日抵减支出；转账、调账和作废交易不计入收支。</p></section>
              <section class="panel"><h2>支出分类</h2><p v-if="!categoryStats.length" class="empty-state">本期暂无支出</p><div v-for="c in categoryStats" :key="c.name" class="resource-row"><span>{{ c.name }}</span><strong>{{ money(c.amount) }}</strong></div></section>
            </div>
            <section v-if="activeView === '总览'" class="panel mvp-spaced"><div class="panel-head"><h2>最近交易</h2><button class="text-link" @click="activeView = '交易'">查看全部 →</button></div><p v-if="!filtered.length" class="empty-state">暂无交易，点击「记一笔」开始。</p><button v-for="t in filtered.slice(0, 5)" :key="t.id" class="mvp-transaction" @click="selectedId = t.id"><span class="transaction-icon blue"><UIcon name="i-lucide-arrow-left-right" /></span><span><strong>{{ t.description || kindLabels[t.type] }}</strong><small>{{ t.category?.name || kindLabels[t.type] }} · {{ accountNames(t) }}</small></span><time>{{ localInput(t.occurredAt).replace('T', ' ') }}</time><b>{{ signedAmount(t) }}</b></button></section>
          </template>
          <section v-if="activeView === '交易'">
            <div class="view-toolbar wrap"><input v-model="search" class="search-field" aria-label="搜索交易" placeholder="搜索说明、分类、账户或标签"><select v-model="typeFilter" aria-label="交易类型筛选"><option value="">所有类型</option><option v-for="(label, kind) in kindLabels" :key="kind" :value="kind">{{ label }}</option></select><select v-model="accountFilter" aria-label="账户筛选"><option value="">所有账户</option><option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option></select><label class="check-label"><input v-model="includeVoided" type="checkbox">包含作废</label></div>
            <section class="panel"><div class="panel-head"><h2>交易记录</h2><span class="hint">共 {{ filtered.length }} 笔</span></div><p v-if="!rows.length" class="empty-state">没有符合条件的交易</p><button v-for="t in rows" :key="t.id" class="mvp-transaction" :class="{ voided: t.isVoid }" @click="selectedId = t.id"><span class="transaction-icon blue">{{ kindLabels[t.type] }}</span><span><strong>{{ t.description || kindLabels[t.type] }} {{ t.isVoid ? '（已作废）' : '' }}</strong><small>{{ t.category?.name }} · {{ accountNames(t) }} <span v-for="tag in t.tags" :key="tag.id" class="tag">{{ tag.name }}</span></small></span><time>{{ localInput(t.occurredAt).replace('T', ' ') }}</time><b>{{ signedAmount(t) }}</b></button><div v-if="filtered.length > 20" class="pagination"><UButton label="上一页" color="neutral" :disabled="page <= 1" @click="page--" /><span>{{ page }} / {{ Math.ceil(filtered.length / 20) }}</span><UButton label="下一页" color="neutral" :disabled="page * 20 >= filtered.length" @click="page++" /></div></section>
          </section>
          <section v-if="activeView === '账户'">
            <div class="section-intro"><div><p>账户合计余额</p><h2>{{ money(balance) }}</h2></div><UButton label="新建账户" icon="i-lucide-plus" @click="resourceEditor = { kind: 'accounts' }" /></div>
            <div class="account-card-grid"><article v-for="a in accounts" :key="a.id" class="balance-card"><span>{{ a.type === 'debit' ? '借记账户' : '信用账户' }}</span><div class="card-brand">{{ a.name }}</div><strong>{{ money(minor(a.amount)) }}</strong><small>{{ a.description || a.cardNumber || '余额来自有效交易' }}</small><div><button @click="transactionEditor = { accountId: a.id }">调账</button><button @click="resourceEditor = { kind: 'accounts', item: a }">编辑</button><button class="danger" @click="deleteResource('accounts', a)">删除</button></div></article></div>
          </section>
          <section v-if="activeView === '分类与标签'" class="taxonomy-grid">
            <article class="panel"><div class="panel-head"><h2>分类</h2><UButton label="新建分类" @click="resourceEditor = { kind: 'categories' }" /></div><p v-if="!categories.length" class="empty-state">创建收入、支出分类，让每笔收支有归属。</p><div v-for="c in categories" :key="c.id" class="resource-row"><span><i class="color-dot" :style="{ background: c.iconColor }" /><strong>{{ c.name }}</strong><small>{{ c.purpose === 'income' ? '收入' : '支出' }} · {{ c.parentCategory ? `上级：${c.parentCategory.name}` : '顶级分类' }}</small></span><div><button class="text-link" @click="resourceEditor = { kind: 'categories', item: c }">编辑</button><button class="text-link danger" @click="deleteResource('categories', c)">删除</button></div></div></article>
            <article class="panel"><div class="panel-head"><h2>标签</h2><UButton label="新建标签" @click="resourceEditor = { kind: 'tags' }" /></div><p v-if="!tags.length" class="empty-state">标签可选，用来标记项目、旅行或其他用途。</p><div v-for="tag in tags" :key="tag.id" class="resource-row"><span><i class="color-dot" :style="{ background: tag.color }" />{{ tag.name }}</span><div><button class="text-link" @click="resourceEditor = { kind: 'tags', item: tag }">编辑</button><button class="text-link danger" @click="deleteResource('tags', tag)">删除</button></div></div></article>
          </section>
        </template>
      </main>
    </div>
    <UModal :open="!!transactionEditor" :dismissible="false" title="交易表单" @update:open="value => { if (!value) transactionEditor = null }"><template #content><TransactionEditor v-if="transactionEditor" v-bind="transactionEditor" :accounts="accounts" :categories="categories" :tags="tags" :transactions="transactions" @close="transactionEditor = null" @saved="saved" /></template></UModal>
    <UModal :open="!!resourceEditor" :dismissible="false" title="资源表单" @update:open="value => { if (!value) resourceEditor = null }"><template #content><ResourceEditor v-if="resourceEditor" v-bind="resourceEditor" :categories="categories" @close="resourceEditor = null" @saved="saved" /></template></UModal>
    <UModal :open="!!selected && !transactionEditor && !confirmation" title="交易详情" @update:open="value => { if (!value) selectedId = '' }"><template #body><template v-if="selected"><div class="detail-amount">{{ signedAmount(selected) }}<span class="status-dot">{{ selected.isVoid ? '已作废' : '有效' }}</span></div><dl class="mvp-detail"><dt>类型</dt><dd>{{ kindLabels[selected.type] }}</dd><dt>说明</dt><dd>{{ selected.description || '无' }}</dd><dt>账户</dt><dd>{{ accountNames(selected) }}</dd><dt>分类</dt><dd>{{ selected.category?.name || '不适用' }}</dd><dt>发生时间</dt><dd>{{ localInput(selected.occurredAt).replace('T', ' ') }}</dd><dt>标签</dt><dd>{{ selected.tags.map(t => t.name).join('、') || '无' }}</dd><dt>创建时间</dt><dd>{{ localInput(selected.createdAt).replace('T', ' ') }}</dd><template v-if="selected.voidedAt"><dt>作废时间</dt><dd>{{ localInput(selected.voidedAt).replace('T', ' ') }}</dd></template></dl><p v-if="selected.type === 'expense'" class="info-strip">已退 {{ money(refundTotal) }} · 剩余可退 {{ money(minor(selected.amount) - refundTotal) }}</p><button v-if="selected.refundOfTransactionId" class="text-link" @click="selectedId = selected.refundOfTransactionId">查看原支出 →</button><div v-if="!selected.isVoid" class="composer-actions"><UButton label="编辑交易" color="neutral" @click="transactionEditor = { editing: selected }" /><UButton v-if="selected.type === 'expense'" label="申请退款" :disabled="refundTotal >= minor(selected.amount)" @click="transactionEditor = { refund: selected }" /><UButton label="作废交易" color="error" variant="soft" @click="voidSelected" /></div></template></template></UModal>
    <UModal :open="!!confirmation" :dismissible="!busy" :title="confirmation?.title" @update:open="value => { if (!value && !busy) confirmation = null }"><template #body><p>{{ confirmation?.text }}</p><p v-if="actionError" role="alert" class="error-box">{{ actionError }}</p></template><template #footer><UButton label="取消" color="neutral" :disabled="busy" @click="confirmation = null" /><UButton label="确认操作" color="error" :loading="busy" :disabled="busy" @click="confirmAction" /></template></UModal>
  </UApp>
</template>
