<script setup lang="ts">
import { kindLabels, type Account, type Category, type Tag, type Transaction, type Kind, type RefundSummary } from '~/types/ledger'
import { minor, money, localInput, shanghaiIso } from '~/utils/money'
import { errorMessage } from '~/composables/useLedger'
const props = defineProps<{ accounts: Account[]; categories: Category[]; tags: Tag[]; refundSummary?: RefundSummary | null; editing?: Transaction; refund?: Transaction; accountId?: string }>()
const emit = defineEmits<{ close: []; saved: [] }>()
const busy = ref(false)
const error = ref('')
const form = reactive({
  type: (props.refund ? 'expense_refund' : props.editing?.type || (props.accountId ? 'balance_adjustment' : 'expense')) as Kind,
  amount: String(props.editing?.amount || ''), description: props.editing?.description || '',
  occurredAt: localInput(props.editing?.occurredAt),
  sourceAccountId: props.editing?.sourceAccount?.id || props.accountId || props.accounts[0]?.id || '',
  destinationAccountId: props.editing?.destinationAccount?.id || props.accounts[1]?.id || props.accounts[0]?.id || '',
  categoryId: props.editing?.category?.id || '', tagIds: props.editing?.tags.map(t => t.id) || [],
  balanceAdjustmentDirection: props.editing?.balanceAdjustmentDirection || 'increase',
})
const hasRefunds = computed(() => props.editing?.type === 'expense' && (props.refundSummary?.activeRefundCount || 0) > 0)
const locked = computed(() => !!hasRefunds.value || props.editing?.type === 'expense_refund')
const categoryOptions = computed(() => props.categories.filter(c => c.purpose === form.type))
const remaining = computed(() => props.refund ? (props.refundSummary?.remainingRefundableAmountMinor || 0) : 0)
watch(() => form.type, () => { form.categoryId = '' })
async function save() {
  if (busy.value) return
  error.value = ''
  let amount: number
  try { amount = minor(form.amount) } catch (e) { error.value = (e as Error).message; return }
  if (amount <= 0) { error.value = '请输入大于 0 的金额'; return }
  if (props.refund && amount > remaining.value) { error.value = '退款不能超过剩余可退金额'; return }
  let occurredAt: string
  try { occurredAt = shanghaiIso(form.occurredAt) } catch (e) { error.value = (e as Error).message; return }
  if (!locked.value && !props.refund) {
    if (['income', 'expense'].includes(form.type) && !form.categoryId) { error.value = '请先创建并选择相应用途的分类'; return }
    if (form.type === 'transfer' && form.sourceAccountId === form.destinationAccountId) { error.value = '转账必须选择两个不同账户'; return }
    if (!(form.type === 'income' ? form.destinationAccountId : form.sourceAccountId)) { error.value = '请先创建并选择账户'; return }
  }
  const meta = { description: form.description.trim() || null, occurredAt }
  let body: object
  if (props.refund) body = { ...meta, amount: amount / 100, refundOfTransactionId: props.refund.id }
  else if (locked.value) body = { ...meta, tagIds: form.tagIds }
  else body = { ...meta, amount: amount / 100, type: form.type, tagIds: form.tagIds,
    sourceAccountId: form.type === 'income' ? null : form.sourceAccountId,
    destinationAccountId: ['income', 'transfer'].includes(form.type) ? form.destinationAccountId : null,
    categoryId: ['income', 'expense'].includes(form.type) ? form.categoryId : null,
    balanceAdjustmentDirection: form.type === 'balance_adjustment' ? form.balanceAdjustmentDirection : null }
  busy.value = true
  try {
    await $fetch(`/api/v1/transactions${props.refund ? '/refunds' : props.editing ? `/${props.editing.id}` : ''}`, { method: props.editing ? 'PATCH' : 'POST', body, retry: 0 })
    emit('saved')
  } catch (e) { error.value = errorMessage(e) }
  finally { busy.value = false }
}
</script>

<template>
  <form class="composer" :aria-busy="busy" @submit.prevent="save">
    <header><div><p class="eyebrow">记录真实的每一笔</p><h2>{{ refund ? '支出退款' : editing ? '编辑交易' : '记一笔' }}</h2></div><button type="button" aria-label="关闭" :disabled="busy" @click="emit('close')">×</button></header>
    <p v-if="refund" class="info-strip">{{ refund.description || '原支出' }} · 剩余可退 {{ money(remaining) }}，退回 {{ refund.sourceAccount?.name }}。</p>
    <p v-if="locked" class="info-strip">此交易仅可修改说明、发生时间和标签。</p>
    <fieldset :disabled="busy" :aria-disabled="busy">
      <label v-if="!refund">交易类型<select v-model="form.type" :disabled="!!editing"><option v-for="kind in (['expense', 'income', 'transfer', 'balance_adjustment'] as const)" :key="kind" :value="kind">{{ kindLabels[kind] }}</option><option v-if="form.type === 'expense_refund'" value="expense_refund">退款</option></select></label>
      <label>金额（元）<input v-model="form.amount" inputmode="decimal" placeholder="0.00" :disabled="locked" required></label>
      <template v-if="!refund && !locked">
        <label v-if="form.type !== 'income'">{{ form.type === 'transfer' ? '转出账户' : '账户' }}<select v-model="form.sourceAccountId" required><option value="" disabled>请选择账户</option><option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }} · {{ money(minor(a.amount)) }}</option></select></label>
        <label v-if="form.type === 'income' || form.type === 'transfer'">{{ form.type === 'transfer' ? '转入账户' : '收款账户' }}<select v-model="form.destinationAccountId" required><option value="" disabled>请选择账户</option><option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option></select></label>
        <label v-if="form.type === 'balance_adjustment'">调整方向<select v-model="form.balanceAdjustmentDirection"><option value="increase">增加余额</option><option value="decrease">减少余额</option></select></label>
        <label v-if="['income', 'expense'].includes(form.type)">分类<select v-model="form.categoryId" required><option value="" disabled>请选择分类</option><option v-for="c in categoryOptions" :key="c.id" :value="c.id">{{ c.parentCategory ? `${c.parentCategory.name} / ` : '' }}{{ c.name }}</option></select></label>
        <p v-if="['income', 'expense'].includes(form.type) && !categoryOptions.length" class="hint">请关闭表单，先在「分类与标签」中新建{{ kindLabels[form.type] }}分类。</p>
      </template>
      <label>发生时间<input v-model="form.occurredAt" type="datetime-local" required></label>
      <label>说明<input v-model="form.description" placeholder="记下这笔交易的用途"></label>
      <div v-if="!refund && tags.length" class="tag-picker"><label v-for="tag in tags" :key="tag.id" class="check-label"><input v-model="form.tagIds" type="checkbox" :value="tag.id">{{ tag.name }}</label></div>
    </fieldset>
    <p v-if="error" role="alert" aria-live="assertive" class="error-box">{{ error }}</p>
    <div class="composer-actions"><span>保存后同步账户余额</span><UButton type="submit" :loading="busy" :aria-busy="busy" :disabled="busy" label="保存交易" /></div>
  </form>
</template>
