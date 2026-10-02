<script setup lang="ts">
import { kindLabels, type Account, type Category, type Tag, type Transaction, type Kind, type RefundSummary } from '~/types/ledger'
import { minor, money, localInput, shanghaiIso } from '~/utils/money'
import { errorMessage } from '~/composables/useLedger'
import { amountExpression, appendAmount, calculateAmount, deleteAmount, emptyAmountDraft, parseAmountInput, setAmountOperator, updateAmount } from '~/utils/amountKeypad'
import { buildCategoryTree, type CategoryTreeNode } from '~/utils/categoryTree'

const props = defineProps<{
  accounts: Account[]
  categories: Category[]
  tags: Tag[]
  resourcesLoading: boolean
  resourcesLoaded: boolean
  resourcesError: string
  refreshResources: () => Promise<boolean>
  refundSummary?: RefundSummary | null
  editing?: Transaction
  refund?: Transaction
  accountId?: string
}>()
const emit = defineEmits<{ close: []; saved: [keepOpen: boolean]; busy: [value: boolean] }>()

const busy = ref(false)
const error = ref('')
const fieldErrors = reactive<Record<string, string>>({})
const editorBody = ref<HTMLElement | null>(null)
const resourceEditor = ref<{ kind: 'accounts' | 'categories' | 'tags'; initialPurpose?: Category['purpose'] } | null>(null)
const resourceBusy = ref(false)
const resourceSyncing = ref(false)
const createdResource = ref<{ kind: 'accounts' | 'categories' | 'tags'; resource: Account | Category | Tag } | null>(null)
let resourceTrigger: HTMLElement | null = null
let resourceFocusKind: 'accounts' | 'categories' | 'tags' = 'accounts'
const resourcesUnavailable = computed(() => !props.resourcesLoaded)
const showEmptyResources = computed(() => props.resourcesLoaded && !props.resourcesLoading && !props.resourcesError)
const missingAccounts = computed(() => !props.refund && !locked.value && (!props.accounts.length || (form.type === 'transfer' && props.accounts.length < 2)))
const accountPlaceholder = computed(() => resourcesUnavailable.value ? (props.resourcesLoading ? '正在读取账户…' : '账户读取失败') : !props.accounts.length ? '暂无账户' : '请选择账户')
const resourceTitle = computed(() => resourceEditor.value?.kind === 'categories'
  ? `新建${resourceEditor.value.initialPurpose === 'income' ? '收入' : '支出'}分类`
  : resourceEditor.value?.kind === 'tags' ? '新建标签' : '新建账户')
const amountDraft = ref(emptyAmountDraft(String(props.editing?.amount || '')))
const form = reactive({
  type: (props.refund ? 'expense_refund' : props.editing?.type || (props.accountId ? 'balance_adjustment' : 'expense')) as Kind,
  amount: amountDraft.value.value,
  description: props.editing?.description || '',
  occurredAt: localInput(props.editing?.occurredAt),
  sourceAccountId: props.editing?.sourceAccount?.id || props.accountId || props.accounts[0]?.id || '',
  destinationAccountId: props.editing?.destinationAccount?.id || props.accounts[1]?.id || props.accounts[0]?.id || '',
  categoryId: props.editing?.category?.id || '',
  tagIds: props.editing?.tags.map(tag => tag.id) || [],
  balanceAdjustmentDirection: props.editing?.balanceAdjustmentDirection || 'increase' as 'increase' | 'decrease',
})
const hasRefunds = computed(() => props.editing?.type === 'expense' && (props.refundSummary?.activeRefundCount || 0) > 0)
const locked = computed(() => !!hasRefunds.value || props.editing?.type === 'expense_refund')
const remaining = computed(() => props.refund ? (props.refundSummary?.remainingRefundableAmountMinor || 0) : 0)
const selectableCategoryIds = computed(() => {
  if (form.type !== 'income' && form.type !== 'expense') return new Set<string>()
  const ids = new Set<string>()
  const visit = (nodes: CategoryTreeNode[]) => nodes.forEach(node => { ids.add(node.category.id); visit(node.children) })
  visit(buildCategoryTree(props.categories, form.type).roots)
  return ids
})
const kindItems = [
  { label: kindLabels.expense, value: 'expense', icon: 'i-lucide-receipt-text' },
  { label: kindLabels.income, value: 'income', icon: 'i-lucide-circle-arrow-down-left' },
  { label: kindLabels.transfer, value: 'transfer', icon: 'i-lucide-arrow-left-right' },
  { label: kindLabels.balance_adjustment, value: 'balance_adjustment', icon: 'i-lucide-scale' },
]
const accountItems = computed(() => props.accounts.map(account => ({ label: `${account.name} · ${money(minor(account.amount))}`, value: account.id })))
const destinationItems = computed(() => props.accounts.map(account => ({ label: account.name, value: account.id })))
const tagItems = computed(() => props.tags.map(tag => ({ label: tag.name, value: tag.id })))
const selectedCategory = computed(() => props.categories.find(category => category.id === form.categoryId))
const selectedCategoryPath = computed(() => {
  if (!selectedCategory.value) return ''
  const find = (nodes: CategoryTreeNode[]): string => {
    for (const node of nodes) {
      if (node.category.id === form.categoryId) return node.path
      const match = find(node.children)
      if (match) return match
    }
    return ''
  }
  return find(buildCategoryTree(props.categories, selectedCategory.value.purpose).roots) || selectedCategory.value.name
})
const expression = computed(() => amountExpression(amountDraft.value))
const amountDisplay = computed(() => expression.value || form.amount)
const amountKeys = ['1', '2', '3', '⌫', '4', '5', '6', '+', '7', '8', '9', '-', 'clear', '0', '.', '='] as const

watch(() => form.type, () => { form.categoryId = '' })

function createResource(kind: 'accounts' | 'categories' | 'tags', event: MouseEvent) {
  if (busy.value || props.resourcesLoading || props.resourcesError) return
  resourceTrigger = event.currentTarget as HTMLElement
  resourceFocusKind = kind
  resourceEditor.value = { kind, ...(kind === 'categories' ? { initialPurpose: form.type as Category['purpose'] } : {}) }
}

// 只在服务器资源同步成功后选中新资源，避免刷新失败时提交列表中不存在的 ID。
watch(() => [props.accounts, props.categories, props.tags], () => {
  const created = createdResource.value
  if (!created) return
  const { kind, resource } = created
  if (kind === 'accounts' && props.accounts.some(account => account.id === resource.id)) {
    if (!form.sourceAccountId) form.sourceAccountId = resource.id
    if (!form.destinationAccountId || (form.type === 'transfer' && form.destinationAccountId === form.sourceAccountId && form.sourceAccountId !== resource.id)) form.destinationAccountId = resource.id
  } else if (kind === 'categories' && selectableCategoryIds.value.has(resource.id)) {
    form.categoryId = resource.id
  } else if (kind === 'tags' && props.tags.some(tag => tag.id === resource.id)) {
    if (!form.tagIds.includes(resource.id)) form.tagIds.push(resource.id)
  } else return
  createdResource.value = null
  clearErrors()
})

async function resourceSaved(resource: Account | Category | Tag) {
  if (!resourceEditor.value) return
  createdResource.value = { kind: resourceEditor.value.kind, resource }
  resourceSyncing.value = true
  try {
    await props.refreshResources()
  } finally {
    resourceSyncing.value = false
    resourceEditor.value = null
  }
}

function restoreResourceFocus(event: Event) {
  event.preventDefault()
  if (resourceTrigger?.isConnected && !resourceTrigger.hasAttribute('disabled')) resourceTrigger.focus({ preventScroll: true })
  else {
    const section = editorBody.value?.querySelector(`[data-resource-field="${resourceFocusKind}"]`)
    const target = section?.querySelector<HTMLElement>('button:not(:disabled), input:not(:disabled)')
      || editorBody.value?.querySelector<HTMLElement>('[data-resource-retry]')
    target?.focus({ preventScroll: true })
  }
}

function updateAmountInput(value: string) {
  if (!validAmountCharacters(value)) return
  amountDraft.value = props.editing || props.refund ? updateAmount(amountDraft.value, value) : parseAmountInput(value)
  form.amount = amountDraft.value.value
  clearErrors()
}

function validAmountCharacters(value: string) {
  return (props.editing || props.refund ? /^[0-9.]*$/ : /^[0-9. +\-]*$/).test(value)
}

function onAmountBeforeInput(event: InputEvent) {
  if (event.data && !validAmountCharacters(event.data)) event.preventDefault()
}

function onAmountPaste(event: ClipboardEvent) {
  if (!validAmountCharacters(event.clipboardData?.getData('text/plain') || '')) event.preventDefault()
}

function onAmountDrop(event: DragEvent) {
  if (!validAmountCharacters(event.dataTransfer?.getData('text/plain') || '')) event.preventDefault()
}

function onAmountInput(event: Event) {
  // 不可取消的输入法事件等路径仍可能修改 DOM，恢复上一次有效显示。
  const input = event.target as HTMLInputElement
  if (!validAmountCharacters(input.value)) input.value = amountDisplay.value
}

function pressAmount(key: string) {
  if (busy.value || locked.value) return
  try {
    if (key === 'clear') amountDraft.value = emptyAmountDraft()
    else if (key === '⌫') amountDraft.value = deleteAmount(amountDraft.value)
    else if (key === '+' || key === '-') amountDraft.value = setAmountOperator(amountDraft.value, key)
    else if (key === '=') amountDraft.value = calculateAmount(amountDraft.value)
    else amountDraft.value = appendAmount(amountDraft.value, key)
    form.amount = amountDraft.value.value
    clearErrors()
  } catch (cause) { fail((cause as Error).message, 'amount') }
}

function onAmountKeydown(event: KeyboardEvent) {
  if (event.ctrlKey || event.metaKey || event.altKey) return
  if (event.key.length === 1 && !validAmountCharacters(event.key) && !(event.key === '=' && !props.editing && !props.refund)) {
    event.preventDefault()
    return
  }
  if (props.editing || props.refund) return
  if (['+', '-', '='].includes(event.key)) { event.preventDefault(); pressAmount(event.key); return }
  if (event.key === 'Backspace' && !form.amount && amountDraft.value.terms.length) {
    event.preventDefault()
    pressAmount('⌫')
    return
  }
  if (amountDraft.value.calculated && /^[\d.]$/.test(event.key)) {
    event.preventDefault()
    pressAmount(event.key)
  }
}

function clearErrors() {
  error.value = ''
  Object.keys(fieldErrors).forEach(key => delete fieldErrors[key])
}

function fail(message: string, field?: string) {
  error.value = message
  if (field) fieldErrors[field] = message
  return false
}

async function save(keepOpen = false) {
  if (busy.value || resourceEditor.value) return
  clearErrors()
  if (!props.refund && !locked.value && resourcesUnavailable.value) { fail(props.resourcesLoading ? '资源正在读取，请稍后再保存' : '资源读取失败，请重试后再保存'); return }
  let amount: number
  try {
    // 保存可以结算完整算式，但失败时保留用户看到的操作数与算式。
    const submittedAmount = amountDraft.value.terms.length ? calculateAmount(amountDraft.value).value : form.amount
    amount = minor(submittedAmount)
  } catch (cause) {
    fail((cause as Error).message, 'amount')
    return
  }
  if (amount <= 0) { fail('请输入大于 0 的金额', 'amount'); return }
  if (props.refund && amount > remaining.value) { fail('退款不能超过剩余可退金额', 'amount'); return }

  let occurredAt: string
  try {
    occurredAt = shanghaiIso(form.occurredAt)
  } catch (cause) {
    fail((cause as Error).message, 'occurredAt')
    return
  }
  if (!locked.value && !props.refund) {
    if (['income', 'expense'].includes(form.type) && !selectableCategoryIds.value.has(form.categoryId)) { fail('请选择有效的相应用途分类', 'categoryId'); return }
    if (form.type === 'transfer' && (!form.destinationAccountId || form.sourceAccountId === form.destinationAccountId)) { fail('转账必须选择两个不同账户', 'destinationAccountId'); return }
    if (!(form.type === 'income' ? form.destinationAccountId : form.sourceAccountId)) { fail('请先创建并选择账户', form.type === 'income' ? 'destinationAccountId' : 'sourceAccountId'); return }
  }

  const meta = { description: form.description.trim() || null, occurredAt }
  let body: object
  if (props.refund) body = { ...meta, amount: amount / 100, refundOfTransactionId: props.refund.id }
  else if (locked.value) body = { ...meta, tagIds: form.tagIds }
  else body = {
    ...meta,
    amount: amount / 100,
    type: form.type,
    tagIds: form.tagIds,
    sourceAccountId: form.type === 'income' ? null : form.sourceAccountId,
    destinationAccountId: ['income', 'transfer'].includes(form.type) ? form.destinationAccountId : null,
    categoryId: ['income', 'expense'].includes(form.type) ? form.categoryId : null,
    balanceAdjustmentDirection: form.type === 'balance_adjustment' ? form.balanceAdjustmentDirection : null,
  }

  busy.value = true
  emit('busy', true)
  try {
    await useApi()(`/api/v1/transactions${props.refund ? '/refunds' : props.editing ? `/${props.editing.id}` : ''}`, {
      method: props.editing ? 'PATCH' : 'POST',
      body,
      retry: 0,
    })
    if (keepOpen && !props.editing && !props.refund) {
      form.amount = ''
      form.description = ''
      amountDraft.value = emptyAmountDraft()
      emit('saved', true)
    } else emit('saved', false)
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
    emit('busy', false)
  }
}
</script>

<template>
  <UForm :state="form" class="modal-editor-form" :class="{ 'transaction-editor-form--compact': !refund }" :disabled="busy" :aria-busy="busy" @submit="save(false)">
    <header class="modal-editor-header">
      <div>
        <p v-if="refund" class="eyebrow">交易信息</p>
        <h2>{{ refund ? '支出退款' : editing ? '编辑交易' : '记一笔' }}</h2>
      </div>
      <UButton color="neutral" variant="ghost" icon="i-lucide-x" aria-label="关闭" :disabled="busy" @click="emit('close')" />
    </header>

    <div ref="editorBody" class="modal-editor-body">
      <UAlert v-if="refund" color="info" variant="soft" icon="i-lucide-rotate-ccw" title="退款摘要" :description="`${refund.description || '原支出'} · 剩余可退 ${money(remaining)} · 退回 ${refund.sourceAccount?.name || '原账户'}`" />
      <UAlert v-if="locked" color="warning" variant="soft" icon="i-lucide-lock-keyhole" title="部分字段已锁定" description="此交易仅可修改说明、发生时间和标签。" />
      <p v-if="resourcesLoading" role="status" class="flex items-center gap-2 text-sm text-muted"><UIcon name="i-lucide-loader-circle" class="animate-spin motion-reduce:animate-none" aria-hidden="true" />{{ resourcesLoaded ? '正在更新账户、分类和标签…' : '正在读取账户、分类和标签…' }}</p>
      <UAlert v-if="resourcesError" color="error" variant="soft" icon="i-lucide-circle-alert" title="资源读取失败" :description="`${resourcesError}${resourcesLoaded ? ' 当前显示上次成功读取的数据。' : ''}${createdResource ? ` 已创建「${createdResource.resource.name}」，重试同步即可继续，无需重复创建。` : ''}`" role="alert">
        <template #actions><UButton data-resource-retry type="button" color="error" variant="soft" label="重试读取资源" :loading="resourcesLoading" :disabled="busy || resourcesLoading" @click="refreshResources" /></template>
      </UAlert>

      <div class="transaction-editor-fields">
      <UFormField v-if="!refund" name="type" label="交易类型" :ui="{ label: 'sr-only' }" required>
        <URadioGroup
          v-model="form.type"
          class="transaction-type-radio-group"
          :items="kindItems"
          :disabled="!!editing"
          name="transaction-type"
          aria-label="交易类型"
          orientation="horizontal"
          variant="card"
          indicator="hidden"
          :ui="{ item: 'relative min-w-0 min-h-11 flex-1 p-2 justify-center items-center', base: 'not-sr-only absolute inset-0 size-full opacity-0 z-10 cursor-pointer', wrapper: 'min-w-0 justify-center', label: 'text-center leading-5', icon: 'hidden' }"
        />
      </UFormField>

      <UFormField v-if="!refund && !locked && ['income', 'expense'].includes(form.type)" data-resource-field="categories" name="categoryId" label="分类" :error="fieldErrors.categoryId" :ui="{ label: 'sr-only', hint: 'min-w-0 max-w-[70%]' }" required>
        <p v-if="selectedCategory" class="transaction-category-selection mb-2"><UIcon class="shrink-0" name="i-lucide-circle-check" aria-hidden="true" /><span>已选择：{{ selectedCategoryPath }}</span></p>
        <TransactionCategoryPicker v-if="selectableCategoryIds.size || showEmptyResources" v-model="form.categoryId" :categories="categories" :purpose="form.type as 'income' | 'expense'" :disabled="busy" @create="createResource('categories', $event)" />
      </UFormField>

      <UFormField name="amount" label="金额（元）" :error="fieldErrors.amount" :class="{ 'transaction-amount-field': !refund }" :ui="{ label: refund ? undefined : 'sr-only' }" required>
        <p v-if="expression" class="transaction-amount-expression">按 = 查看结果，也可直接保存结算</p>
        <UInput
          :model-value="amountDisplay" inputmode="decimal" placeholder="0.00" :disabled="locked"
          class="w-full" :class="{ 'transaction-amount-input': !refund, 'transaction-amount-input--expression': !!expression }"
          :ui="!refund ? { base: 'text-left ps-10 pe-4 rounded-[var(--ui-radius)] ring-0 focus-visible:ring-2 focus-visible:ring-primary' } : undefined"
          @update:model-value="updateAmountInput" @keydown="onAmountKeydown"
          @beforeinput="onAmountBeforeInput" @paste="onAmountPaste" @drop="onAmountDrop" @input="onAmountInput"
        >
          <template v-if="!refund" #leading><span class="transaction-amount-currency" aria-hidden="true">¥</span></template>
        </UInput>
        <div v-if="!editing && !refund" class="transaction-amount-keypad" role="group" aria-label="金额键盘">
          <UButton
            v-for="key in amountKeys" :key="key" type="button" class="transaction-amount-key"
            :ui="{ base: 'rounded-[var(--ui-radius)]' }"
            :class="{ 'transaction-amount-key--operator': key === '+' || key === '-', 'transaction-amount-key--equal': key === '=', 'transaction-amount-key--clear': key === 'clear' }"
            :color="['+', '-', '='].includes(key) ? 'primary' : 'neutral'"
            :variant="key === '=' ? 'solid' : 'soft'"
            :icon="key === '⌫' ? 'i-lucide-delete' : undefined"
            :label="key === '⌫' ? undefined : key === 'clear' ? '清空' : key"
            :aria-label="key === '⌫' ? '删除一位' : key === '=' ? '计算结果' : key === 'clear' ? '清空金额' : key"
            :disabled="busy" @click="pressAmount(key)"
          />
        </div>
      </UFormField>

      <div class="transaction-editor-details" :class="{ 'transaction-editor-details--refund': refund }">
      <template v-if="!refund && !locked">
        <UFormField v-if="form.type !== 'income'" data-resource-field="accounts" name="sourceAccountId" :error="fieldErrors.sourceAccountId" :label="form.type === 'transfer' ? '转出账户' : '账户'" required>
          <USelect v-model="form.sourceAccountId" :items="accountItems" :placeholder="accountPlaceholder" :disabled="resourcesUnavailable || !accounts.length" :aria-describedby="missingAccounts && showEmptyResources ? 'transaction-account-empty' : undefined" class="w-full" />
        </UFormField>
        <UFormField v-if="form.type === 'income' || form.type === 'transfer'" data-resource-field="accounts" name="destinationAccountId" :error="fieldErrors.destinationAccountId" :label="form.type === 'transfer' ? '转入账户' : '收款账户'" required>
          <USelect v-model="form.destinationAccountId" :items="destinationItems" :placeholder="accountPlaceholder" :disabled="resourcesUnavailable || !accounts.length" :aria-describedby="missingAccounts && showEmptyResources ? 'transaction-account-empty' : undefined" class="w-full" />
        </UFormField>
        <div v-if="missingAccounts && showEmptyResources" class="transaction-editor-detail-wide flex flex-wrap items-center gap-2 rounded-lg bg-elevated p-3">
          <p id="transaction-account-empty" role="status" class="text-sm text-muted">{{ accounts.length ? '转账需要两个不同账户，请再创建一个账户。' : '暂无账户，先创建账户后即可记账。' }}</p>
          <UButton type="button" color="neutral" variant="outline" icon="i-lucide-plus" label="新建账户" :disabled="busy" @click="createResource('accounts', $event)" />
        </div>
        <UFormField v-if="form.type === 'balance_adjustment'" name="balanceAdjustmentDirection" label="调整方向" required>
          <USelect v-model="form.balanceAdjustmentDirection" :items="[{ label: '增加余额', value: 'increase' }, { label: '减少余额', value: 'decrease' }]" class="w-full" />
        </UFormField>
      </template>

      <UFormField name="occurredAt" label="发生时间" :error="fieldErrors.occurredAt" required>
        <UInput v-model="form.occurredAt" type="datetime-local" class="w-full" />
      </UFormField>
      <UFormField name="description" label="说明" class="transaction-editor-detail-wide">
        <UInput v-model="form.description" placeholder="记下这笔交易的用途" class="w-full" />
      </UFormField>
      <UFormField v-if="!refund && (tags.length || showEmptyResources)" data-resource-field="tags" name="tagIds" label="标签" class="transaction-editor-detail-wide">
        <UCheckboxGroup v-if="tags.length" v-model="form.tagIds" :items="tagItems" orientation="horizontal" class="transaction-tag-group" />
        <div v-else class="flex flex-wrap items-center gap-2">
          <p role="status" class="text-sm text-muted">暂无标签，可直接保存。</p>
          <UButton type="button" color="neutral" variant="link" icon="i-lucide-plus" label="新建标签" :disabled="busy" @click="createResource('tags', $event)" />
        </div>
      </UFormField>
      </div>
      </div>

      <UAlert v-if="error" color="error" variant="soft" icon="i-lucide-circle-alert" title="保存失败" :description="error" role="alert" aria-live="polite" />
    </div>
    <div class="modal-editor-actions transaction-editor-actions">
      <UButton v-if="!editing && !refund" type="button" label="保存再记" color="neutral" variant="soft" size="lg" :disabled="busy" @click="save(true)" />
      <UButton type="submit" :label="editing || refund ? '保存交易' : '完成'" size="lg" :loading="busy" :aria-busy="busy" :disabled="busy" />
    </div>
  </UForm>
  <UModal :open="!!resourceEditor" :title="resourceTitle" :dismissible="!resourceBusy && !resourceSyncing" :content="{ onCloseAutoFocus: restoreResourceFocus }" :ui="{ content: 'motion-reduce:animate-none motion-reduce:transition-none' }" @update:open="value => { if (!value && !resourceBusy && !resourceSyncing) resourceEditor = null }">
    <template #content>
      <ResourceEditor v-if="resourceEditor" v-bind="resourceEditor" :categories="categories" :disabled="resourceSyncing" @busy="resourceBusy = $event" @close="() => { if (!resourceSyncing) resourceEditor = null }" @saved="resourceSaved" />
    </template>
  </UModal>
</template>

<style scoped>
.transaction-type-radio-group :deep([data-slot="fieldset"]) { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 4px; padding: 4px; border-radius: var(--ui-radius); background: var(--ui-bg-muted); }
.transaction-type-radio-group :deep([data-slot="item"]) { min-width: 0; border: 0; border-radius: calc(var(--ui-radius) - 4px); background: transparent; }
.transaction-type-radio-group :deep([data-slot="item"]:has([data-state="checked"])) { background: var(--ui-bg); box-shadow: 0 1px 4px color-mix(in srgb, var(--ui-text) 12%, transparent); }
.transaction-type-radio-group :deep([data-slot="item"]:has(:focus-visible)) { outline: 2px solid var(--ui-primary); outline-offset: 1px; }
.transaction-type-radio-group :deep([data-slot="label"]) { overflow-wrap: anywhere; }
.transaction-editor-form--compact .modal-editor-header { align-items: center; padding-top: 12px; }
.transaction-editor-form--compact .modal-editor-header h2 { font-size: 1.125rem; }
.transaction-editor-form--compact .modal-editor-body { padding-block: 12px; }
.transaction-editor-form--compact .transaction-editor-fields { gap: 12px; }
.transaction-category-selection { display: inline-flex; align-items: center; gap: 4px; min-width: 0; max-width: 100%; color: var(--ui-primary); font-size: .8125rem; }
.transaction-amount-input :deep(input) { min-height: 72px; font-family: var(--font-sans); font-size: clamp(2rem, 4vw, 2.75rem); font-weight: 600; font-variant-numeric: lining-nums tabular-nums; line-height: 1.2; letter-spacing: -.025em; background: var(--ui-bg-muted); color: var(--ui-primary); }
.transaction-amount-currency { color: var(--ui-primary); font-size: 1.5rem; }
.transaction-amount-input--expression :deep(input) { min-height: 48px; padding-block: 8px; font-size: clamp(1.25rem, 3vw, 2rem); letter-spacing: 0; }
.transaction-amount-expression { display: flex; gap: 8px; min-width: 0; margin: 0 0 6px; font-size: .8125rem; color: var(--ui-text-muted); }
.transaction-amount-keypad { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px; margin-top: 8px; }
.transaction-amount-key { min-width: 0; min-height: 48px; align-items: center; justify-content: center; font-size: 1.375rem; line-height: 1; font-weight: 500; font-variant-numeric: tabular-nums; }
.transaction-amount-key:not(.transaction-amount-key--operator):not(.transaction-amount-key--equal) { background: var(--ui-bg-muted); }
.transaction-amount-key--clear { font-size: .875rem; }
.transaction-amount-key:not(:disabled):active { background: var(--ui-bg-accented); }
.transaction-amount-key--operator:not(:disabled):active { background: var(--pt-primary-container); }
.transaction-amount-key--equal:not(:disabled):active { background: color-mix(in srgb, var(--ui-primary) 80%, var(--ui-bg-inverted)); }
.transaction-editor-details { display: grid; min-width: 0; gap: 12px; }
.transaction-editor-details--refund { gap: 14px; }
.transaction-editor-actions { justify-content: flex-end; }
.transaction-editor-actions :deep(button) { min-width: 104px; justify-content: center; }
@media (min-width: 640px) {
  .transaction-editor-details:not(.transaction-editor-details--refund) { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .transaction-editor-detail-wide { grid-column: 1 / -1; }
}
@media (max-width: 560px) {
  .transaction-editor-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .transaction-editor-actions :deep(button:only-child) { grid-column: 1 / -1; }
}
</style>
