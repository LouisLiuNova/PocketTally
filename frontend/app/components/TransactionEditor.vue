<script setup lang="ts">
import { kindLabels, type Account, type Category, type Tag, type Transaction, type Kind, type RefundSummary } from '~/types/ledger'
import { minor, money, localInput, shanghaiIso } from '~/utils/money'
import { errorMessage } from '~/composables/useLedger'

const props = defineProps<{
  accounts: Account[]
  categories: Category[]
  tags: Tag[]
  refundSummary?: RefundSummary | null
  editing?: Transaction
  refund?: Transaction
  accountId?: string
}>()
const emit = defineEmits<{ close: []; saved: []; busy: [value: boolean] }>()

const busy = ref(false)
const error = ref('')
const fieldErrors = reactive<Record<string, string>>({})
const form = reactive({
  type: (props.refund ? 'expense_refund' : props.editing?.type || (props.accountId ? 'balance_adjustment' : 'expense')) as Kind,
  amount: String(props.editing?.amount || ''),
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
const categoryOptions = computed(() => props.categories.filter(category => category.purpose === form.type))
const remaining = computed(() => props.refund ? (props.refundSummary?.remainingRefundableAmountMinor || 0) : 0)
const kindItems = [
  { label: kindLabels.expense, value: 'expense' },
  { label: kindLabels.income, value: 'income' },
  { label: kindLabels.transfer, value: 'transfer' },
  { label: kindLabels.balance_adjustment, value: 'balance_adjustment' },
]
const accountItems = computed(() => props.accounts.map(account => ({ label: `${account.name} · ${money(minor(account.amount))}`, value: account.id })))
const destinationItems = computed(() => props.accounts.map(account => ({ label: account.name, value: account.id })))
const categoryItems = computed(() => categoryOptions.value.map(category => ({
  label: `${category.parentCategory ? `${category.parentCategory.name} / ` : ''}${category.name}`,
  value: category.id,
})))
const tagItems = computed(() => props.tags.map(tag => ({ label: tag.name, value: tag.id })))

watch(() => form.type, () => { form.categoryId = '' })

function clearErrors() {
  error.value = ''
  Object.keys(fieldErrors).forEach(key => delete fieldErrors[key])
}

function fail(message: string, field?: string) {
  error.value = message
  if (field) fieldErrors[field] = message
  return false
}

async function save() {
  if (busy.value) return
  clearErrors()
  let amount: number
  try {
    amount = minor(form.amount)
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
    if (['income', 'expense'].includes(form.type) && !form.categoryId) { fail('请先创建并选择相应用途的分类', 'categoryId'); return }
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
    await $fetch(`/api/v1/transactions${props.refund ? '/refunds' : props.editing ? `/${props.editing.id}` : ''}`, {
      method: props.editing ? 'PATCH' : 'POST',
      body,
      retry: 0,
    })
    emit('saved')
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
    emit('busy', false)
  }
}
</script>

<template>
  <UForm :state="form" class="transaction-editor" :disabled="busy" :aria-busy="busy" @submit="save">
    <header class="transaction-editor-header">
      <div>
        <p class="eyebrow">记录真实的每一笔</p>
        <h2>{{ refund ? '支出退款' : editing ? '编辑交易' : '记一笔' }}</h2>
      </div>
      <UButton color="neutral" variant="ghost" icon="i-lucide-x" aria-label="关闭" :disabled="busy" @click="emit('close')" />
    </header>

    <UAlert v-if="refund" color="info" variant="soft" icon="i-lucide-rotate-ccw" title="退款摘要" :description="`${refund.description || '原支出'} · 剩余可退 ${money(remaining)} · 退回 ${refund.sourceAccount?.name || '原账户'}`" />
    <UAlert v-if="locked" color="warning" variant="soft" icon="i-lucide-lock-keyhole" title="部分字段已锁定" description="此交易仅可修改说明、发生时间和标签。" />

    <div class="transaction-editor-fields">
      <UFormField v-if="!refund" name="type" label="交易类型" required>
        <USelect v-model="form.type" :items="kindItems" :disabled="!!editing" class="w-full" />
      </UFormField>

      <UFormField name="amount" label="金额（元）" :error="fieldErrors.amount" required>
        <UInput v-model="form.amount" inputmode="decimal" placeholder="0.00" :disabled="locked" class="w-full" />
      </UFormField>

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
        <UFormField v-if="['income', 'expense'].includes(form.type)" name="categoryId" label="分类" :error="fieldErrors.categoryId" required>
          <USelect v-model="form.categoryId" :items="categoryItems" placeholder="请选择分类" class="w-full" />
        </UFormField>
        <p v-if="['income', 'expense'].includes(form.type) && !categoryItems.length" class="hint">请关闭表单，先在「分类与标签」中新建{{ kindLabels[form.type] }}分类。</p>
      </template>

      <UFormField name="occurredAt" label="发生时间" :error="fieldErrors.occurredAt" required>
        <UInput v-model="form.occurredAt" type="datetime-local" class="w-full" />
      </UFormField>
      <UFormField name="description" label="说明">
        <UInput v-model="form.description" placeholder="记下这笔交易的用途" class="w-full" />
      </UFormField>
      <UFormField v-if="!refund && tags.length" name="tagIds" label="标签">
        <UCheckboxGroup v-model="form.tagIds" :items="tagItems" orientation="horizontal" class="transaction-tag-group" />
      </UFormField>
    </div>

    <UAlert v-if="error" color="error" variant="soft" icon="i-lucide-circle-alert" title="保存失败" :description="error" role="alert" aria-live="polite" />
    <div class="transaction-editor-actions">
      <span class="hint">保存后同步账户余额</span>
      <UButton type="submit" label="保存交易" :loading="busy" :aria-busy="busy" :disabled="busy" />
    </div>
  </UForm>
</template>
