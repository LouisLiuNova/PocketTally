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
  refundSummary?: RefundSummary | null
  editing?: Transaction
  refund?: Transaction
  accountId?: string
}>()
const emit = defineEmits<{ close: []; saved: [keepOpen: boolean]; busy: [value: boolean] }>()

const busy = ref(false)
const error = ref('')
const fieldErrors = reactive<Record<string, string>>({})
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
const amountKeys = ['7', '8', '9', '⌫', '4', '5', '6', '+', '1', '2', '3', '-', 'clear', '0', '.', '='] as const

watch(() => form.type, () => { form.categoryId = '' })

function updateAmountInput(value: string) {
  amountDraft.value = props.editing || props.refund ? updateAmount(amountDraft.value, value) : parseAmountInput(value)
  form.amount = amountDraft.value.value
  clearErrors()
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
  if (props.editing || props.refund || event.ctrlKey || event.metaKey || event.altKey) return
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
  if (busy.value) return
  clearErrors()
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
    if (form.type === 'transfer' && form.sourceAccountId === form.destinationAccountId) { fail('转账必须选择两个不同账户', 'destinationAccountId'); return }
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
        <p class="eyebrow">交易信息</p>
        <h2>{{ refund ? '支出退款' : editing ? '编辑交易' : '记一笔' }}</h2>
      </div>
      <UButton color="neutral" variant="ghost" icon="i-lucide-x" aria-label="关闭" :disabled="busy" @click="emit('close')" />
    </header>

    <div class="modal-editor-body">
      <UAlert v-if="refund" color="info" variant="soft" icon="i-lucide-rotate-ccw" title="退款摘要" :description="`${refund.description || '原支出'} · 剩余可退 ${money(remaining)} · 退回 ${refund.sourceAccount?.name || '原账户'}`" />
      <UAlert v-if="locked" color="warning" variant="soft" icon="i-lucide-lock-keyhole" title="部分字段已锁定" description="此交易仅可修改说明、发生时间和标签。" />

      <div class="transaction-editor-fields">
      <UFormField v-if="!refund" name="type" label="交易类型" required>
        <URadioGroup
          v-model="form.type"
          class="transaction-type-radio-group"
          :items="kindItems"
          :disabled="!!editing"
          name="transaction-type"
          aria-label="交易类型"
          orientation="horizontal"
          variant="card"
          :ui="{ item: 'min-w-0 min-h-11 flex-1 p-2 grid grid-cols-[1rem_1fr_1rem] items-center gap-2', container: 'm-0', wrapper: 'min-w-0', label: 'text-center leading-5' }"
        />
      </UFormField>

      <UFormField v-if="!refund && !locked && ['income', 'expense'].includes(form.type)" name="categoryId" label="分类" :error="fieldErrors.categoryId" :ui="{ hint: 'min-w-0 max-w-[70%]' }" required>
        <p v-if="selectedCategory" class="transaction-category-selection mb-2"><UIcon class="shrink-0" name="i-lucide-circle-check" aria-hidden="true" /><span>已选择：{{ selectedCategoryPath }}</span></p>
        <TransactionCategoryPicker v-model="form.categoryId" :categories="categories" :purpose="form.type as 'income' | 'expense'" :disabled="busy" />
      </UFormField>

      <UFormField name="amount" label="金额（元）" :error="fieldErrors.amount" :class="{ 'transaction-amount-field': !refund }" required>
        <p v-if="expression" class="transaction-amount-expression">按 = 查看结果，也可直接保存结算</p>
        <UInput
          :model-value="amountDisplay" inputmode="decimal" placeholder="0.00" :disabled="locked"
          class="w-full" :class="{ 'transaction-amount-input': !refund, 'transaction-amount-input--expression': !!expression }"
          :ui="!refund ? { base: 'text-right ps-10 pe-4 rounded-[var(--ui-radius)]' } : undefined"
          @update:model-value="updateAmountInput" @keydown="onAmountKeydown"
        >
          <template v-if="!refund" #leading><span class="transaction-amount-currency" aria-hidden="true">¥</span></template>
        </UInput>
        <div v-if="!editing && !refund" class="transaction-amount-keypad" role="group" aria-label="金额键盘">
          <UButton
            v-for="key in amountKeys" :key="key" type="button" class="transaction-amount-key"
            :ui="{ base: 'rounded-[var(--ui-radius)]' }"
            :class="{ 'transaction-amount-key--operator': key === '+' || key === '-', 'transaction-amount-key--equal': key === '=', 'transaction-amount-key--clear': key === 'clear' }"
            :color="['+', '-', '='].includes(key) ? 'primary' : 'neutral'"
            :variant="key === '=' ? 'solid' : ['+', '-'].includes(key) ? 'soft' : 'outline'"
            :icon="key === '⌫' ? 'i-lucide-delete' : undefined"
            :label="key === '⌫' ? undefined : key === 'clear' ? '清空' : key"
            :aria-label="key === '⌫' ? '删除一位' : key === '=' ? '计算结果' : key === 'clear' ? '清空金额' : key"
            :disabled="busy" @click="pressAmount(key)"
          />
        </div>
      </UFormField>

      <div class="transaction-editor-details" :class="{ 'transaction-editor-details--refund': refund }">
      <template v-if="!refund && !locked">
        <UFormField v-if="form.type !== 'income'" name="sourceAccountId" :label="form.type === 'transfer' ? '转出账户' : '账户'" required>
          <USelect v-model="form.sourceAccountId" :items="accountItems" placeholder="请选择账户" class="w-full" />
        </UFormField>
        <UFormField v-if="form.type === 'income' || form.type === 'transfer'" name="destinationAccountId" :label="form.type === 'transfer' ? '转入账户' : '收款账户'" required>
          <USelect v-model="form.destinationAccountId" :items="destinationItems" placeholder="请选择账户" class="w-full" />
        </UFormField>
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
      <UFormField v-if="!refund && tags.length" name="tagIds" label="标签" class="transaction-editor-detail-wide">
        <UCheckboxGroup v-model="form.tagIds" :items="tagItems" orientation="horizontal" class="transaction-tag-group" />
      </UFormField>
      </div>
      </div>

      <UAlert v-if="error" color="error" variant="soft" icon="i-lucide-circle-alert" title="保存失败" :description="error" role="alert" aria-live="polite" />
    </div>
    <div class="modal-editor-actions transaction-editor-actions">
      <UButton type="submit" :label="editing || refund ? '保存交易' : '完成'" :loading="busy" :aria-busy="busy" :disabled="busy" />
      <UButton v-if="!editing && !refund" type="button" label="保存再记" color="neutral" variant="outline" :disabled="busy" @click="save(true)" />
    </div>
  </UForm>
</template>

<style scoped>
.transaction-type-radio-group :deep([data-slot="fieldset"]) {
  gap: 8px;
}

.transaction-type-radio-group :deep([data-slot="item"]) {
  min-width: 0;
}

.transaction-type-radio-group :deep([data-slot="item"]:has([data-state="checked"])) {
  border-color: var(--pt-focus-ring);
  background: var(--pt-primary-container);
  box-shadow: inset 0 0 0 1px var(--pt-focus-ring);
}

.transaction-type-radio-group :deep([data-slot="label"]) {
  overflow-wrap: anywhere;
}

.transaction-editor-form--compact .modal-editor-body { padding-block: 14px; }
.transaction-editor-form--compact .transaction-editor-fields { gap: 12px; }
.transaction-category-selection { display: inline-flex; align-items: center; gap: 4px; min-width: 0; max-width: 100%; color: var(--ui-primary); font-size: .8125rem; }
.transaction-amount-input :deep(input) {
  min-height: 64px;
  font-family: var(--font-sans);
  font-size: clamp(2rem, 4vw, 2.5rem);
  font-weight: 600;
  font-variant-numeric: lining-nums tabular-nums;
  line-height: 1.2;
  letter-spacing: -.025em;
  background: var(--ui-bg-muted);
}
.transaction-amount-currency { color: var(--ui-text-muted); font-size: 1.25rem; }
.transaction-amount-input--expression :deep(input) { font-size: clamp(1.25rem, 3vw, 2rem); letter-spacing: 0; }
.transaction-amount-expression { display: flex; gap: 8px; min-width: 0; margin: 0 0 6px; font-size: .8125rem; color: var(--ui-text-muted); }
.transaction-amount-expression span { flex-shrink: 0; }
.transaction-amount-expression output { min-width: 0; overflow-x: auto; white-space: nowrap; font-variant-numeric: tabular-nums; }
.transaction-amount-keypad { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px; margin-top: 8px; }
.transaction-amount-key { min-width: 0; min-height: 44px; align-items: center; justify-content: center; font-size: 1.125rem; line-height: 1; font-weight: 500; font-variant-numeric: tabular-nums; }
.transaction-amount-key--clear { font-size: .875rem; }
.transaction-amount-key:not(:disabled):active { background: var(--ui-bg-accented); }
.transaction-amount-key--operator:not(:disabled):active { background: var(--pt-primary-container); }
.transaction-amount-key--equal:not(:disabled):active { background: color-mix(in srgb, var(--ui-primary) 80%, var(--ui-bg-inverted)); }
.transaction-editor-details { display: grid; min-width: 0; gap: 12px; }
.transaction-editor-details--refund { gap: 14px; }

@media (min-width: 640px) {
  .transaction-editor-details:not(.transaction-editor-details--refund) { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .transaction-editor-detail-wide { grid-column: 1 / -1; }
}

@media (max-width: 560px) {
  .transaction-type-radio-group :deep([data-slot="fieldset"]) {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
