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
import { accountNames, signedAmount } from '~/utils/transactionDisplay'

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
let searchTimer: ReturnType<typeof setTimeout> | undefined
let requestId = 0
let stopRouteWatch: (() => void) | undefined

const routeState = computed(() => parseTransactionQuery(route.query, today).state)
const pageCount = computed(() => Math.max(1, Math.ceil(transactionTotal.value / 20)))

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
    if (state.page > lastPage) {
      await updateRoute({ page: lastPage }, true, false)
    }
  } catch (error) {
    if (currentRequest === requestId) queryError.value = errorMessage(error)
  } finally {
    if (currentRequest === requestId) loading.value = false
  }
}

async function updateRoute(patch: Partial<TransactionRouteState>, replace = false, resetPage = true) {
  const next = { ...routeState.value, ...patch }
  if (resetPage && patch.page === undefined) next.page = 1
  return navigateTo(
    { path: '/transactions', query: compactQuery(serializeTransactionState(next, today)) },
    { replace },
  )
}

function selectValue(event: Event) {
  return (event.target as HTMLSelectElement).value
}

function scheduleSearch(event: Event) {
  searchDraft.value = (event.target as HTMLInputElement).value
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => void updateRoute({ q: searchDraft.value.trim() }, true), 250)
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

async function synchronizeRoute() {
  const parsed = parseTransactionQuery(route.query, today)
  if (!queriesEqual(route.query, parsed.query)) {
    await navigateTo({ path: '/transactions', query: compactQuery(parsed.query) }, { replace: true })
    return
  }
  searchDraft.value = parsed.state.q
  startDraft.value = parsed.state.start
  endDraft.value = parsed.state.end
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
  <div class="page-flow page-flow--transactions">
  <div class="view-toolbar transaction-filters">
    <input :value="searchDraft" class="search-field" aria-label="搜索交易" placeholder="搜索说明、分类、账户或标签" @input="scheduleSearch">
    <label>开始日期<input v-model="startDraft" type="date" @change="commitDates"></label>
    <label>结束日期（不含）<input v-model="endDraft" type="date" @change="commitDates"></label>
    <select :value="routeState.type" aria-label="交易类型筛选" @change="updateRoute({ type: selectValue($event) as TransactionRouteState['type'] })"><option value="">所有类型</option><option v-for="(label, kind) in kindLabels" :key="kind" :value="kind">{{ label }}</option></select>
    <select :value="routeState.accountId" aria-label="账户筛选" @change="updateRoute({ accountId: selectValue($event) })"><option value="">所有账户</option><option v-for="account in workspace.accounts.value" :key="account.id" :value="account.id">{{ account.name }}</option></select>
    <select :value="routeState.categoryId" aria-label="分类筛选" @change="updateRoute({ categoryId: selectValue($event) })"><option value="">所有分类</option><option v-for="category in workspace.categories.value" :key="category.id" :value="category.id">{{ category.name }}</option></select>
    <select :value="routeState.tagId" aria-label="标签筛选" @change="updateRoute({ tagId: selectValue($event) })"><option value="">所有标签</option><option v-for="tag in workspace.tags.value" :key="tag.id" :value="tag.id">{{ tag.name }}</option></select>
    <select :value="routeState.status" aria-label="状态筛选" @change="updateRoute({ status: selectValue($event) as TransactionRouteState['status'] })"><option value="active">仅有效</option><option value="voided">仅作废</option><option value="all">全部状态</option></select>
  </div>
  <p v-if="dateError" role="alert" class="error-box">{{ dateError }}</p>
  <div v-if="queryError" role="alert" class="error-box">{{ queryError }}<UButton label="重试" color="neutral" @click="loadTransactions" /></div>
  <p v-if="loading && !transactions.length" role="status" class="empty-state">正在读取分页流水…</p>
  <section class="panel">
    <div class="panel-head"><h2>交易记录</h2><span class="hint">服务端共 {{ transactionTotal }} 笔</span></div>
    <p v-if="!loading && !transactions.length" class="empty-state">没有符合条件的交易</p>
    <button v-for="transaction in transactions" :key="transaction.id" class="mvp-transaction" :class="{ voided: transaction.isVoid }" @click="workspace.openTransaction(transaction)">
      <span class="transaction-icon blue">{{ kindLabels[transaction.type] }}</span>
      <span><strong>{{ transaction.description || kindLabels[transaction.type] }} {{ transaction.isVoid ? '（已作废）' : '' }}</strong><small>{{ transaction.category?.name }} · {{ accountNames(transaction) }} <span v-for="tag in transaction.tags" :key="tag.id" class="tag">{{ tag.name }}</span></small></span>
      <time>{{ localInput(transaction.occurredAt).replace('T', ' ') }}</time><b>{{ signedAmount(transaction) }}</b>
    </button>
    <div v-if="transactionTotal > 20" class="pagination">
      <UButton label="上一页" color="neutral" :disabled="routeState.page <= 1" @click="updateRoute({ page: routeState.page - 1 }, false, false)" />
      <span>{{ routeState.page }} / {{ pageCount }}</span>
      <UButton label="下一页" color="neutral" :disabled="routeState.page >= pageCount" @click="updateRoute({ page: routeState.page + 1 }, false, false)" />
    </div>
  </section>
  </div>
</template>
