<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type { ImportBatch, ImportChange, ImportHistory, ImportRow, ImportStatus } from '~/types/imports'
import { importStatusLabels } from '~/types/imports'
import { errorMessage } from '~/composables/useLedger'
import { localInput, money } from '~/utils/money'

const api = useApi()
const ledger = useLedger()
const route = useRoute()
const router = useRouter()
const file = ref<File>()
const batch = ref<ImportBatch>()
const history = ref<ImportHistory>()
const historyPage = ref(1)
const busy = ref(false)
const loading = ref(false)
const error = ref('')
const status = ref<ImportStatus | 'all'>('all')
const page = ref(1)
const bulkPayment = ref<string>('')
const bulkAccount = ref<string>()
const bulkCategory = ref<string>()
const bulkType = ref<'income' | 'expense'>('expense')
const remember = ref(true)
const confirmOpen = ref(false)
const deleteOpen = ref(false)
const editing = ref<ImportRow>()
const editorOpen = ref(false)
const edit = reactive({ type: 'expense' as 'income' | 'expense', accountId: '', categoryId: '', amount: '', occurredAt: '', description: '' })
let requestVersion = 0
const accountItems = computed(() => ledger.accounts.value.map(a => ({ label: a.name, value: a.id })))
const categoryItems = (type: string) => ledger.categories.value.filter(c => c.purpose === type).map(c => ({ label: c.name, value: c.id }))
const historyItems = computed(() => history.value?.items.map(b => ({ label: `${b.filename} · ${b.status === 'draft' ? '草稿' : '已提交'}`, value: b.id })) || [])
const statusItems = [{ label: '全部状态', value: 'all' }, ...Object.entries(importStatusLabels).map(([value, label]) => ({ label, value }))]
const paymentItems = computed(() => (batch.value?.paymentKeys || []).map(value => ({ label: value, value })))
const columns: TableColumn<ImportRow>[] = [
  { accessorKey: 'included', header: '纳入' }, { accessorKey: 'description', header: '来源记录' },
  { accessorKey: 'amountMinor', header: '金额与时间' }, { accessorKey: 'accountId', header: '账户与分类' },
  { accessorKey: 'status', header: '状态' }, { accessorKey: 'actions', header: '操作' },
]
const canSubmit = computed(() => batch.value?.status === 'draft' && batch.value.summary.selectedCount > 0 && batch.value.summary.unresolvedCount === 0 && !busy.value && !loading.value)

async function loadHistory() {
  try { history.value = await api<ImportHistory>('/api/v1/imports', { query: { page: historyPage.value, pageSize: 20 } }) }
  catch (e) { error.value = errorMessage(e) }
}
async function loadBatch(id = String(route.query.batchId || '')) {
  const version = ++requestVersion
  if (!id) { batch.value = undefined; loading.value = false; return }
  loading.value = true
  try {
    const result = await api<ImportBatch>(`/api/v1/imports/${id}`, { query: { page: page.value, pageSize: 50, ...(status.value !== 'all' ? { status: status.value } : {}) } })
    if (version === requestVersion) { batch.value = result; error.value = '' }
  } catch (e) { if (version === requestVersion) error.value = errorMessage(e) }
  finally { if (version === requestVersion) loading.value = false }
}
async function selectBatch(id: string) {
  if (busy.value) return
  page.value = 1; status.value = 'all'; error.value = ''; batch.value = undefined
  await router.replace({ query: { ...route.query, batchId: id } })
}
async function upload() {
  if (!file.value || busy.value) return
  busy.value = true; error.value = ''
  const body = new FormData(); body.append('file', file.value)
  try {
    const result = await api<ImportBatch>('/api/v1/imports', { method: 'POST', body })
    batch.value = result; page.value = 1; status.value = 'all'
    await router.replace({ query: { batchId: result.id } }); await loadHistory()
    file.value = undefined
  } catch (e) { error.value = errorMessage(e) }
  finally { busy.value = false }
}
async function apply(changes: ImportChange[]) {
  if (!batch.value || busy.value) return false
  busy.value = true; error.value = ''
  try {
    const result = await api<ImportBatch>(`/api/v1/imports/${batch.value.id}`, { method: 'PATCH', body: { version: batch.value.version, changes } })
    batch.value = result; await loadBatch(result.id)
    return true
  } catch (e) { error.value = errorMessage(e); return false }
  finally { busy.value = false }
}
async function applyBulk() {
  if (!bulkPayment.value || (!bulkAccount.value && !bulkCategory.value)) { error.value = '请选择支付方式及账户或分类'; return }
  const changes: ImportChange[] = []
  if (bulkAccount.value) changes.push({ paymentKey: bulkPayment.value, accountId: bulkAccount.value, rememberMapping: remember.value })
  if (bulkCategory.value) changes.push({ paymentKey: bulkPayment.value, matchType: bulkType.value, categoryId: bulkCategory.value })
  await apply(changes)
}
function openEditor(row: ImportRow) {
  editing.value = row
  Object.assign(edit, { type: row.type || 'expense', accountId: row.accountId || '', categoryId: row.categoryId || '', amount: (row.amountMinor / 100).toFixed(2), occurredAt: row.occurredAt ? `${localInput(row.occurredAt)}:${String(new Date(row.occurredAt).getUTCSeconds()).padStart(2, '0')}` : '', description: row.description })
  editorOpen.value = true
}
async function saveEditor() {
  if (!editing.value) return
  if (!/^\d+(\.\d{1,2})?$/.test(edit.amount) || !edit.occurredAt) { error.value = '请输入正数金额和完整发生时间'; return }
  const [integer, fraction = ''] = edit.amount.split('.')
  const amountMinor = Number(integer) * 100 + Number(fraction.padEnd(2, '0'))
  if (!Number.isSafeInteger(amountMinor) || amountMinor <= 0) { error.value = '金额超出范围或不是正数'; return }
  const occurredAt = new Date(`${edit.occurredAt}+08:00`)
  if (!Number.isFinite(occurredAt.getTime())) { error.value = '发生时间无效'; return }
  if (await apply([{ rowIds: [editing.value.id], type: edit.type, accountId: edit.accountId || null, categoryId: edit.categoryId || null, amountMinor, occurredAt: occurredAt.toISOString(), description: edit.description }])) editorOpen.value = false
}
async function submit() {
  if (!batch.value || busy.value) return
  busy.value = true; error.value = ''
  try {
    batch.value = await api<ImportBatch>(`/api/v1/imports/${batch.value.id}/commit`, { method: 'POST', body: { version: batch.value.version } })
    confirmOpen.value = false; status.value = 'all'; page.value = 1
    await loadHistory(); await ledger.refreshResources()
  } catch (e) { error.value = errorMessage(e) }
  finally { busy.value = false }
}
async function removeDraft() {
  if (!batch.value || busy.value) return
  busy.value = true; error.value = ''
  try {
    await api(`/api/v1/imports/${batch.value.id}`, { method: 'DELETE', query: { version: batch.value.version } })
    deleteOpen.value = false; batch.value = undefined
    await router.replace({ query: {} }); await loadHistory()
  } catch (e) { error.value = errorMessage(e) }
  finally { busy.value = false }
}
function showTransactions() {
  const source = batch.value?.summary.source
  const start = source?.startAt ? localInput(source.startAt).slice(0, 10) : ''
  const endDate = source?.endAt ? new Date(source.endAt) : new Date()
  endDate.setUTCDate(endDate.getUTCDate() + 1)
  return navigateTo({ path: '/transactions', query: { start, end: localInput(endDate.toISOString()).slice(0, 10) } })
}
watch(() => route.query.batchId, () => { batch.value = undefined; error.value = ''; void loadBatch() }, { immediate: true })
watch(status, () => { page.value = 1; void loadBatch() })
watch(page, () => { void loadBatch() })
watch(historyPage, () => { void loadHistory() })
watch(bulkType, () => { bulkCategory.value = undefined })
watch(() => edit.type, () => { if (!categoryItems(edit.type).some(c => c.value === edit.categoryId)) edit.categoryId = '' })
await loadHistory()
</script>

<template>
  <div class="page-flow space-y-5">
    <UAlert v-if="error" color="error" title="操作未完成" :description="error" role="alert" />
    <UAlert v-if="ledger.loadError.value" color="error" title="账户或分类读取失败" :description="ledger.loadError.value">
      <template #actions><UButton label="重试读取资源" @click="ledger.refreshResources()" /></template>
    </UAlert>
    <UCard>
      <div class="grid gap-5 lg:grid-cols-2">
        <div class="space-y-3">
          <h2 class="font-semibold">上传个人账单</h2>
          <p class="text-sm text-muted">支付宝 CSV、微信 CSV/XLSX，最多 10 MiB、10,000 行。退款识别后跳过，请单独核对。</p>
          <UFileUpload v-model="file" accept=".csv,.xlsx" label="选择账单文件" description="CSV 或 XLSX" :disabled="busy" />
          <UButton label="解析账单" icon="i-lucide-file-input" :loading="busy" :disabled="!file || loading" @click="upload" />
        </div>
        <div class="space-y-3">
          <h2 class="font-semibold">导入历史与草稿</h2>
          <USelect :model-value="batch?.id" :items="historyItems" aria-label="选择导入批次" placeholder="选择已保存的批次" class="w-full" :disabled="busy" @update:model-value="selectBatch(String($event))" />
          <div class="flex items-center gap-2">
            <UButton label="上一页历史" color="neutral" variant="ghost" :disabled="historyPage === 1 || busy" @click="historyPage--" />
            <span class="text-sm">第 {{ historyPage }} 页</span>
            <UButton label="下一页历史" color="neutral" variant="ghost" :disabled="!history || historyPage * 20 >= history.total || busy" @click="historyPage++" />
          </div>
        </div>
      </div>
    </UCard>
    <div v-if="loading && !batch" role="status" aria-label="正在读取导入批次"><USkeleton class="h-40" /></div>
    <template v-if="batch">
      <UCard>
        <div class="flex flex-wrap justify-between gap-4">
          <div class="min-w-0">
            <h2 class="break-all font-semibold">{{ batch.filename }}</h2>
            <p class="text-sm text-muted">{{ batch.provider === 'alipay' ? '支付宝' : '微信支付' }} · {{ batch.summary.inputRows }} 条来源记录 · {{ batch.status === 'draft' ? '草稿已保存' : '导入已完成' }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <UButton label="重新读取" color="neutral" variant="outline" :disabled="busy || loading" @click="loadBatch()" />
            <UButton v-if="batch.status === 'draft'" label="删除草稿" color="error" variant="ghost" :disabled="busy" @click="deleteOpen = true" />
            <UButton v-else label="查看导入期间交易" @click="showTransactions" />
          </div>
        </div>
        <div class="mt-4 flex flex-wrap gap-2">
          <UBadge v-for="(count, key) in batch.summary.counts" :key="key" color="neutral" variant="soft">{{ importStatusLabels[key as ImportStatus] }} {{ count }}</UBadge>
        </div>
        <p v-if="batch.summary.counts.refund_pending" class="mt-3 text-sm text-warning">退款未入账，因此账本净支出可能与平台扣除退款后的摘要不同。</p>
      </UCard>
      <UCard v-if="batch.status === 'draft'">
        <template #header><h3 class="font-semibold">批量映射与分类</h3></template>
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <UFormField label="来源支付方式"><USelect v-model="bulkPayment" :items="paymentItems" placeholder="选择支付方式" class="w-full" :disabled="busy || loading" /></UFormField>
          <UFormField label="映射账户"><USelect v-model="bulkAccount" :items="accountItems" placeholder="选择已有账户" class="w-full" :disabled="busy || loading" /></UFormField>
          <UFormField label="分类用途"><USelect v-model="bulkType" :items="[{ label: '支出', value: 'expense' }, { label: '收入', value: 'income' }]" class="w-full" :disabled="busy" /></UFormField>
          <UFormField label="批量分类"><USelect v-model="bulkCategory" :items="categoryItems(bulkType)" placeholder="选择已有分类" class="w-full" :disabled="busy || loading" /></UFormField>
        </div>
        <div class="mt-4 flex flex-wrap items-center gap-4">
          <UCheckbox v-model="remember" label="提交成功后记住账户映射" :disabled="busy" />
          <UButton label="应用到该支付方式" :disabled="busy || loading || !bulkPayment" @click="applyBulk" />
          <UButton v-if="!accountItems.length" to="/accounts" label="创建账户或调账" color="neutral" variant="outline" />
          <UButton v-if="!categoryItems(bulkType).length" to="/categories" label="创建分类" color="neutral" variant="outline" />
        </div>
      </UCard>
      <UCard :ui="{ body: 'p-0 sm:p-0' }">
        <template #header>
          <div class="flex flex-wrap items-center justify-between gap-3">
            <h3 class="font-semibold">预览与修正</h3>
            <USelect v-model="status" :items="statusItems" aria-label="筛选导入状态" :disabled="busy" />
          </div>
        </template>
        <UTable :data="batch.items" :columns="columns" :loading="loading" caption="账单导入候选" empty="没有符合此状态的记录" :ui="{ td: 'align-top', th: 'whitespace-nowrap' }">
          <template #included-cell="{ row }"><UCheckbox :model-value="row.original.included" :aria-label="`纳入第 ${row.original.rowNumber} 行`" :disabled="busy || loading || !row.original.editable" @update:model-value="apply([{ rowIds: [row.original.id], included: Boolean($event) }])" /></template>
          <template #description-cell="{ row }">
            <div class="max-w-72 break-words whitespace-normal"><strong>{{ row.original.description || '无说明' }}</strong><p class="mt-1 text-xs text-muted">第 {{ row.original.rowNumber }} 行 · {{ row.original.sourceId || '无单号' }}</p><p class="text-xs text-muted">{{ row.original.paymentKey || '未提供支付方式' }}</p></div>
          </template>
          <template #amountMinor-cell="{ row }"><div class="whitespace-nowrap font-medium">{{ row.original.type === 'income' ? '+' : row.original.type === 'expense' ? '−' : '' }}{{ money(row.original.amountMinor) }}</div><time class="text-xs text-muted">{{ row.original.occurredAt ? localInput(row.original.occurredAt).replace('T', ' ') : '时间无效' }}</time></template>
          <template #accountId-cell="{ row }"><div class="min-w-32 max-w-48 whitespace-normal"><p>{{ ledger.accounts.value.find(a => a.id === row.original.accountId)?.name || (!row.original.editable && row.original.status !== 'imported' ? '—' : '待补账户') }}</p><p class="text-sm text-muted">{{ ledger.categories.value.find(c => c.id === row.original.categoryId)?.name || (!row.original.editable && row.original.status !== 'imported' ? '—' : '待补分类') }}</p></div></template>
          <template #status-cell="{ row }"><UBadge :color="row.original.status === 'ready' || row.original.status === 'imported' ? 'success' : 'neutral'">{{ importStatusLabels[row.original.status] }}</UBadge><p v-if="row.original.reason" class="mt-1 max-w-64 whitespace-normal text-xs text-muted">{{ row.original.reason }}</p><p v-if="row.original.similarTransactionIds.length" class="mt-1 text-xs text-warning">存在相似手工交易，请核对</p><UButton v-if="row.original.duplicateBatchId" label="查看原批次" color="neutral" variant="link" size="xs" @click="selectBatch(row.original.duplicateBatchId!)" /></template>
          <template #actions-cell="{ row }"><UButton :label="row.original.editable ? '修正' : '来源详情'" color="neutral" variant="ghost" :aria-label="`查看第 ${row.original.rowNumber} 行${row.original.editable ? '并修正' : '来源'}`" :disabled="busy || loading" @click="openEditor(row.original)" /></template>
        </UTable>
        <template #footer><div class="flex flex-wrap items-center justify-between gap-3"><span class="text-sm text-muted">共 {{ batch.total }} 条 · 第 {{ page }} 页</span><UPagination v-model:page="page" :total="batch.total" :items-per-page="50" :disabled="busy || loading" /></div></template>
      </UCard>
      <UCard v-if="batch.status === 'draft'">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div><p>纳入 {{ batch.summary.selectedCount }} 条 · 收入 {{ money(batch.summary.incomeMinor) }} · 支出 {{ money(batch.summary.expenseMinor) }}</p><p v-if="batch.summary.unresolvedCount" class="text-sm text-warning">还有 {{ batch.summary.unresolvedCount }} 条待解决记录，请补齐或明确跳过。</p></div>
          <UButton label="确认导入" :disabled="!canSubmit" @click="confirmOpen = true" />
        </div>
      </UCard>
    </template>
    <UModal v-model:open="editorOpen" :title="editing?.editable ? '修正候选记录' : '来源详情'" :dismissible="!busy">
      <template #body>
        <div v-if="editing" class="space-y-4">
          <UAlert v-if="error" color="error" title="修正未保存" :description="error" />
          <dl class="space-y-2 text-sm break-all"><div v-for="(value, key) in editing.original" :key="key"><dt class="text-muted">{{ ({ sourceId: '平台单号', merchantOrderId: '商户单号', counterparty: '交易对方', product: '商品', paymentMethod: '支付方式', platformCategory: '平台类别', platformStatus: '平台状态', direction: '收支', amount: '来源金额', occurredAt: '来源时间', rowNumbers: '来源行号' } as Record<string, string>)[key] }}</dt><dd>{{ Array.isArray(value) ? value.join('、') : value || '—' }}</dd></div></dl>
          <form v-if="editing.editable" id="import-row-editor" class="space-y-4" @submit.prevent="saveEditor">
            <UFormField label="收支类型"><USelect v-model="edit.type" :items="[{ label: '支出', value: 'expense' }, { label: '收入', value: 'income' }]" :disabled="busy" /></UFormField>
            <UFormField label="账户"><USelect v-model="edit.accountId" :items="accountItems" placeholder="选择账户" class="w-full" :disabled="busy" /></UFormField>
            <UFormField label="分类"><USelect v-model="edit.categoryId" :items="categoryItems(edit.type)" placeholder="选择分类" class="w-full" :disabled="busy" /></UFormField>
            <UFormField label="金额（元）"><UInput v-model="edit.amount" inputmode="decimal" :disabled="busy" /></UFormField>
            <UFormField label="发生时间（上海）"><UInput v-model="edit.occurredAt" type="datetime-local" step="1" :disabled="busy" /></UFormField>
            <UFormField label="说明"><UTextarea v-model="edit.description" :disabled="busy" :maxlength="2000" /></UFormField>
          </form>
        </div>
      </template>
      <template #footer><UButton v-if="editing?.editable" label="保存修正" type="submit" form="import-row-editor" :loading="busy" /><UButton label="关闭" color="neutral" variant="outline" :disabled="busy" @click="editorOpen = false" /></template>
    </UModal>
    <UModal v-model:open="confirmOpen" title="确认整批导入" :dismissible="!busy">
      <template #body><div v-if="batch" class="space-y-3"><UAlert v-if="error" color="error" title="导入未完成" :description="error" /><p>将新增 {{ batch.summary.selectedCount }} 条交易，收入 {{ money(batch.summary.incomeMinor) }}，支出 {{ money(batch.summary.expenseMinor) }}。</p><p class="text-sm text-muted">重复、退款、跳过和不支持的记录不会入账。任一纳入记录失败时整批回滚。</p><UButton v-if="error" label="重新预览" color="neutral" variant="outline" @click="confirmOpen = false; loadBatch()" /></div></template>
      <template #footer><UButton label="提交整批" :loading="busy" :disabled="!canSubmit" @click="submit" /><UButton label="取消" color="neutral" variant="outline" :disabled="busy" @click="confirmOpen = false" /></template>
    </UModal>
    <UModal v-model:open="deleteOpen" title="删除未提交草稿" description="仅删除此批次的预览与修正，不影响正式交易。" :dismissible="!busy"><template #footer><UButton label="删除草稿" color="error" :loading="busy" @click="removeDraft" /><UButton label="取消" color="neutral" variant="outline" :disabled="busy" @click="deleteOpen = false" /></template></UModal>
  </div>
</template>
