<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import { kindLabels, type Transaction } from '~/types/ledger'
import { localInput } from '~/utils/money'
import { accountNames, signedAmount } from '~/utils/transactionDisplay'

defineProps<{ transactions: Transaction[]; loading?: boolean }>()
const emit = defineEmits<{ select: [transaction: Transaction] }>()

const columns: TableColumn<Transaction>[] = [
  { accessorKey: 'transaction', header: '交易' },
  { accessorKey: 'account', header: '账户' },
  { accessorKey: 'occurredAt', header: '发生时间' },
  { accessorKey: 'amount', header: '金额' },
  { accessorKey: 'status', header: '状态' },
  { accessorKey: 'actions', header: '操作' },
]

function detailLabel(transaction: Transaction) {
  return `查看详情：${transaction.description || kindLabels[transaction.type]}`
}
</script>

<template>
  <UTable
    :data="transactions"
    :columns="columns"
    :loading="loading"
    :ui="{ root: 'transaction-table', td: 'align-middle', th: 'whitespace-nowrap' }"
    caption="交易记录"
    empty="没有符合条件的交易"
  >
    <template #transaction-cell="{ row }">
      <UButton
        class="transaction-summary-button"
        color="neutral"
        variant="ghost"
        :aria-label="detailLabel(row.original)"
        @click="emit('select', row.original)"
        @keydown.enter.prevent="emit('select', row.original)"
      >
        <span class="transaction-type-mark" :data-kind="row.original.type">{{ kindLabels[row.original.type] }}</span>
        <span class="transaction-summary-copy">
          <strong>{{ row.original.description || kindLabels[row.original.type] }}</strong>
          <span class="transaction-summary-meta">
            <span>{{ row.original.category?.name || '无分类' }}</span>
            <span v-for="tag in row.original.tags" :key="tag.id" class="transaction-tag">{{ tag.name }}</span>
          </span>
          <span class="transaction-summary-mobile-context">{{ accountNames(row.original) || '无账户' }} · {{ localInput(row.original.occurredAt).replace('T', ' ') }} · {{ row.original.isVoid ? '已作废' : '有效' }}</span>
        </span>
      </UButton>
    </template>

    <template #account-cell="{ row }">
      <span class="transaction-account">{{ accountNames(row.original) || '—' }}</span>
    </template>

    <template #occurredAt-cell="{ row }">
      <time :datetime="row.original.occurredAt">{{ localInput(row.original.occurredAt).replace('T', ' ') }}</time>
    </template>

    <template #amount-cell="{ row }">
      <strong class="transaction-amount" :data-kind="row.original.type">{{ signedAmount(row.original) }}</strong>
    </template>

    <template #status-cell="{ row }">
      <span class="transaction-status" :data-voided="row.original.isVoid">
        <UBadge :color="row.original.isVoid ? 'neutral' : 'success'" variant="subtle">{{ row.original.isVoid ? '已作废' : '有效' }}</UBadge>
        <span class="sr-only">{{ row.original.isVoid ? '已作废' : '有效' }}</span>
      </span>
    </template>

    <template #actions-cell="{ row }">
      <UButton color="neutral" variant="ghost" size="sm" :aria-label="detailLabel(row.original)" @click="emit('select', row.original)" @keydown.enter.prevent="emit('select', row.original)">
        详情
      </UButton>
    </template>

    <template #loading>
      <div class="transaction-table-skeleton" aria-label="正在加载交易">
        <USkeleton v-for="index in 5" :key="index" class="h-12 w-full" />
      </div>
    </template>
  </UTable>
</template>
