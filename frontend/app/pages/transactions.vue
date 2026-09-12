<script setup lang="ts">
import { kindLabels, type Page, type Transaction } from '~/types/ledger'
import { errorMessage, type TransactionQuery } from '~/composables/useLedger'
import {
  compactQuery,
  isDate,
  parseTransactionQuery,
  queriesEqual,
  serializeTransactionState,
  type TransactionRouteState,
} from '~/utils/routeQuery'
import { localInput } from '~/utils/money'

const route = useRoute()
const workspace = useLedgerWorkspace()
const today = localInput().slice(0, 10)
const transactions = ref<Transaction[]>([])
const transactionTotal = ref(0)
const loading = ref(false)
const queryError = ref('')
const dateError = ref('')
const searchDraft = ref('')
const startDraft = ref('')
const endDraft = ref('')
const advancedOpen = ref(false)
let searchTimer: ReturnType<typeof setTimeout> | undefined
let requestId = 0
let stopRouteWatch: (() => void) | undefined

const routeState = computed(() => parseTransactionQuery(route.query, today).state)
const pageCount = computed(() => Math.max(1, Math.ceil(transactionTotal.value / 20)))
const activeAdvancedCount = computed(() => [routeState.value.start, routeState.value.end, routeState.value.accountId, routeState.value.categoryId, routeState.value.tagId].filter(Boolean).length)
const hasFilters = computed(() => !!(routeState.value.q || routeState.value.type || routeState.value.accountId || routeState.value.categoryId || routeState.value.tagId || routeState.value.status !== 'active' || routeState.value.start || routeState.value.end))
const filterSummary = computed(() => {
  const state = routeState.value
  const parts = [`${transactionTotal.value} 笔结果`]
  if (state.type) parts.push(kindLabels[state.type])
  if (state.status !== 'active') parts.push(state.status === 'voided' ? '已作废' : '全部状态')
  if (activeAdvancedCount.value) parts.push(`${activeAdvancedCount.value} 个高级条件`)
  return parts.join(' · ')
})

function apiQuery(state: TransactionRouteState): TransactionQuery {
  return {
    page: state.page,
    pageSize: 20,
    startAt: state.start ? new Date(`${state.start}T00:00:00+08:00`).toISOString() : undefined,
    endAt: state.end ? new Date(`${state.end}T00:00:00+08:00`).toISOString() : undefined,
    type: state.type || undefined,
    accountId: state.accountId || undefined,
    categoryId: state.categoryId || undefined,
    includeDescendants: !!state.categoryId,
    tagId: state.tagId || undefined,
    q: state.q || undefined,
    status: state.status,
  }
}

async function loadTransactions(state = routeState.value) {
  const currentRequest = ++requestId
  loading.value = true
  queryError.value = ''
  try {
    const result = await $fetch<Page<Transaction>>('/api/v1/transactions', { query: apiQuery(state) })
    if (currentRequest !== requestId) return
    transactions.value = result.items
    transactionTotal.value = result.total
    const lastPage = Math.max(1, Math.ceil(result.total / 20))
    if (state.page > lastPage) await updateRoute({ page: lastPage }, true, false)
  } catch (error) {
    if (currentRequest === requestId) queryError.value = errorMessage(error)
  } finally {
    if (currentRequest === requestId) loading.value = false
  }
}

async function updateRoute(patch: Partial<TransactionRouteState>, replace = false, resetPage = true) {
  const next = { ...routeState.value, ...patch }
  if (resetPage && patch.page === undefined) next.page = 1
  return navigateTo({ path: '/transactions', query: compactQuery(serializeTransactionState(next, today)) }, { replace })
}

function selectValue(event: Event) {
  return (event.target as HTMLSelectElement).value
}

function scheduleSearch(event: Event) {
  searchDraft.value = (event.target as HTMLInputElement).value
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => void updateRoute({ q: searchDraft.value.trim() }, true), 250)
}

function scheduleSearchValue(value: string) {
  searchDraft.value = value
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => void updateRoute({ q: value.trim() }, true), 250)
}

function commitDates() {
  dateError.value = ''
  if ((startDraft.value && !isDate(startDraft.value)) || (endDraft.value && !isDate(endDraft.value))) {
    dateError.value = '请输入有效日期。'
    return
  }
  if (startDraft.value && endDraft.value && startDraft.value >= endDraft.value) {
    dateError.value = '开始日期必须早于结束日期。'
    return
  }
  void updateRoute({ start: startDraft.value, end: endDraft.value })
}

function clearFilters() {
  searchDraft.value = ''
  startDraft.value = ''
  endDraft.value = ''
  void updateRoute({ q: '', start: '', end: '', type: '', accountId: '', categoryId: '', tagId: '', status: 'active', page: 1 }, true, false)
}

async function synchronizeRoute() {
  const parsed = parseTransactionQuery(route.query, today)
  if (!queriesEqual(route.query, parsed.query)) {
    await navigateTo({ path: '/transactions', query: compactQuery(parsed.query) }, { replace: true })
    return
  }
  searchDraft.value = parsed.state.q
  startDraft.value = parsed.state.start
  endDraft.value = parsed.state.end
  advancedOpen.value = Boolean(
    parsed.state.start || parsed.state.end || parsed.state.accountId || parsed.state.categoryId || parsed.state.tagId
      || route.query.start !== undefined || route.query.end !== undefined || route.query.accountId !== undefined
      || route.query.categoryId !== undefined || route.query.tagId !== undefined,
  )
  dateError.value = ''
  await loadTransactions(parsed.state)
}

onMounted(() => {
  stopRouteWatch = watch(() => route.fullPath, () => void synchronizeRoute(), { immediate: true })
})
watch(workspace.refreshRevision, () => void loadTransactions())
onBeforeUnmount(() => {
  clearTimeout(searchTimer)
  requestId++
  stopRouteWatch?.()
})
</script>

<template>
  <div class="page-flow page-flow--transactions transaction-page">
    <section class="transaction-toolbar" aria-label="交易筛选">
      <div class="transaction-toolbar-primary">
        <UInput v-model="searchDraft" class="transaction-search" icon="i-lucide-search" aria-label="搜索交易" placeholder="搜索说明、分类、账户或标签" @update:model-value="scheduleSearchValue" />
        <label class="native-filter">交易类型<select :value="routeState.type" aria-label="交易类型筛选" @change="updateRoute({ type: selectValue($event) as TransactionRouteState['type'] })"><option value="">所有类型</option><option v-for="(label, kind) in kindLabels" :key="kind" :value="kind">{{ label }}</option></select></label>
        <label class="native-filter">状态<select :value="routeState.status" aria-label="状态筛选" @change="updateRoute({ status: selectValue($event) as TransactionRouteState['status'] })"><option value="active">仅有效</option><option value="voided">仅作废</option><option value="all">全部状态</option></select></label>
        <UButton color="neutral" variant="outline" :icon="advancedOpen ? 'i-lucide-chevron-up' : 'i-lucide-sliders-horizontal'" :label="`高级筛选${activeAdvancedCount ? `（${activeAdvancedCount}）` : ''}`" :aria-expanded="advancedOpen" @click="advancedOpen = !advancedOpen" />
      </div>

      <UCollapsible v-model:open="advancedOpen" class="transaction-advanced-filters">
        <template #content>
          <div class="transaction-advanced-grid">
            <label>开始日期<input v-model="startDraft" type="date" @change="commitDates"></label>
            <label>结束日期（不含）<input v-model="endDraft" type="date" @change="commitDates"></label>
            <label>账户<select :value="routeState.accountId" aria-label="账户筛选" @change="updateRoute({ accountId: selectValue($event) })"><option value="">所有账户</option><option v-for="account in workspace.accounts.value" :key="account.id" :value="account.id">{{ account.name }}</option></select></label>
            <label>分类<select :value="routeState.categoryId" aria-label="分类筛选" @change="updateRoute({ categoryId: selectValue($event) })"><option value="">所有分类</option><option v-for="category in workspace.categories.value" :key="category.id" :value="category.id">{{ category.name }}</option></select></label>
            <label>标签<select :value="routeState.tagId" aria-label="标签筛选" @change="updateRoute({ tagId: selectValue($event) })"><option value="">所有标签</option><option v-for="tag in workspace.tags.value" :key="tag.id" :value="tag.id">{{ tag.name }}</option></select></label>
          </div>
        </template>
      </UCollapsible>
    </section>

    <p v-if="dateError" role="alert" class="error-box">{{ dateError }}</p>
    <div class="transaction-results-bar" role="status" aria-live="polite">
      <span>{{ filterSummary }}</span>
      <span v-if="loading" class="transaction-sync-status">正在同步…</span>
      <UButton v-if="hasFilters" label="清除筛选" color="neutral" variant="link" size="sm" @click="clearFilters" />
    </div>
    <div v-if="queryError" role="alert" class="error-box">{{ queryError }}<UButton label="重试" color="neutral" @click="loadTransactions" /></div>

    <section class="panel transaction-panel">
      <div class="panel-head"><div><p class="eyebrow">流水明细</p><h2>交易记录</h2></div><span class="hint">每页 20 笔 · CNY · Asia/Shanghai</span></div>
      <TransactionTable :transactions="transactions" :loading="loading" @select="workspace.openTransaction" />
      <div v-if="!loading && !transactions.length" class="transaction-empty-state">
        <p>{{ hasFilters ? '没有符合条件的交易' : '还没有交易记录' }}</p>
        <div class="transaction-empty-actions">
          <UButton v-if="hasFilters" label="清除筛选" color="neutral" variant="outline" @click="clearFilters" />
          <UButton v-if="!hasFilters" label="记一笔" icon="i-lucide-plus" @click="workspace.transactionEditor.value = {}" />
        </div>
      </div>
      <div v-if="transactionTotal > 20" class="transaction-pagination" role="navigation" aria-label="交易分页">
        <UButton label="上一页" color="neutral" variant="outline" :disabled="routeState.page <= 1" @click="updateRoute({ page: routeState.page - 1 }, false, false)" />
        <span aria-live="polite">第 {{ routeState.page }} / {{ pageCount }} 页</span>
        <UButton label="下一页" color="neutral" variant="outline" :disabled="routeState.page >= pageCount" @click="updateRoute({ page: routeState.page + 1 }, false, false)" />
      </div>
    </section>
  </div>
</template>
