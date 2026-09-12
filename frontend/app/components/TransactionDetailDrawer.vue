<script setup lang="ts">
import { kindLabels, type RefundSummary, type Transaction } from '~/types/ledger'
import { localInput, money } from '~/utils/money'
import { accountNames, signedAmount } from '~/utils/transactionDisplay'

const props = defineProps<{
  transaction: Transaction | null
  refundSummary: RefundSummary | null
  refundLoading: boolean
  refundError: string
  modal?: boolean
}>()
const emit = defineEmits<{
  close: []
  edit: [transaction: Transaction]
  refund: [transaction: Transaction]
  void: []
  retryRefund: []
  openOriginal: [id: string]
}>()
</script>

<template>
  <USlideover
    :open="!!props.transaction"
    side="right"
    title="交易详情"
    description="查看交易信息与后续操作"
    :close="{ 'aria-label': '关闭交易详情' }"
    :modal="props.modal ?? true"
    :ui="{ content: 'w-full sm:max-w-xl', body: 'space-y-6' }"
    @update:open="value => { if (!value) emit('close') }"
  >
    <template #body>
      <template v-if="props.transaction">
        <div class="transaction-detail-hero">
          <span class="transaction-type-mark" :data-kind="props.transaction.type">{{ kindLabels[props.transaction.type] }}</span>
          <div>
            <p class="eyebrow">{{ props.transaction.isVoid ? '已作废交易' : '有效交易' }}</p>
            <h2>{{ props.transaction.description || kindLabels[props.transaction.type] }}</h2>
          </div>
        </div>

        <div class="transaction-detail-amount" :data-kind="props.transaction.type">
          {{ signedAmount(props.transaction) }}
          <UBadge :color="props.transaction.isVoid ? 'neutral' : 'success'" variant="subtle">{{ props.transaction.isVoid ? '已作废' : '有效' }}</UBadge>
        </div>

        <dl class="transaction-detail-list">
          <div><dt>类型</dt><dd>{{ kindLabels[props.transaction.type] }}</dd></div>
          <div><dt>账户</dt><dd>{{ accountNames(props.transaction) || '不适用' }}</dd></div>
          <div><dt>分类</dt><dd>{{ props.transaction.category?.name || '不适用' }}</dd></div>
          <div><dt>发生时间</dt><dd>{{ localInput(props.transaction.occurredAt).replace('T', ' ') }}（上海）</dd></div>
          <div><dt>标签</dt><dd>{{ props.transaction.tags.map(tag => tag.name).join('、') || '无' }}</dd></div>
          <div v-if="props.transaction.balanceAdjustmentDirection"><dt>调账方向</dt><dd>{{ props.transaction.balanceAdjustmentDirection === 'increase' ? '增加余额' : '减少余额' }}</dd></div>
          <div v-if="props.transaction.voidedAt"><dt>作废时间</dt><dd>{{ localInput(props.transaction.voidedAt).replace('T', ' ') }}</dd></div>
        </dl>

        <UAlert
          v-if="props.transaction.type === 'expense'"
          :color="props.refundError ? 'error' : 'info'"
          variant="soft"
          :icon="props.refundError ? 'i-lucide-circle-alert' : 'i-lucide-receipt-text'"
          :title="props.refundError ? '退款额度读取失败' : '退款额度'"
          :description="props.refundError || (props.refundLoading ? '正在读取退款额度…' : `已退 ${money(props.refundSummary?.refundedAmountMinor || 0)} · 剩余可退 ${money(props.refundSummary?.remainingRefundableAmountMinor || 0)}`)"
          role="alert"
        >
          <template v-if="props.refundError" #actions>
            <UButton label="重试" color="error" variant="soft" @click="emit('retryRefund')" />
          </template>
        </UAlert>

        <UButton
          v-if="props.transaction.refundOfTransactionId"
          color="neutral"
          variant="link"
          label="查看原支出 →"
          @click="emit('openOriginal', props.transaction.refundOfTransactionId)"
        />
      </template>
    </template>

    <template #footer>
      <div v-if="props.transaction && !props.transaction.isVoid" class="transaction-detail-actions">
        <UButton label="编辑交易" color="neutral" variant="outline" @click="emit('edit', props.transaction!)" />
        <UButton
          v-if="props.transaction.type === 'expense'"
          label="申请退款"
          :disabled="props.refundLoading || !!props.refundError || !props.refundSummary?.canRefund"
          @click="emit('refund', props.transaction!)"
          @keydown.enter.prevent="emit('refund', props.transaction!)"
        />
        <UButton label="作废交易" color="error" variant="soft" @click="emit('void')" />
      </div>
    </template>
  </USlideover>
</template>
