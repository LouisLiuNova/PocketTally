<script setup lang="ts">
import type { ExpenseTransactionPage } from '~/types/ledger'
import { localInput, money } from '~/utils/money'

const props = defineProps<{
  open: boolean
  title: string
  loading: boolean
  error: string
  data: ExpenseTransactionPage | null
}>()

const emit = defineEmits<{
  close: []
  retry: []
  openTransaction: [id: string]
}>()
</script>

<template>
  <USlideover
    :open="props.open"
    side="right"
    title="统计明细"
    :description="props.title"
    :close="{ 'aria-label': '关闭统计明细' }"
    :ui="{ content: 'w-full sm:max-w-2xl', body: 'space-y-5' }"
    @update:open="value => { if (!value) emit('close') }"
  >
    <template #body>
      <div class="statistics-drillover-heading">
        <div>
          <p class="text-sm text-muted">当前筛选</p>
          <h2 class="text-lg font-semibold text-highlighted">{{ props.title }}</h2>
        </div>
        <UBadge v-if="props.data" color="neutral" variant="subtle">{{ props.data.total }} 笔</UBadge>
      </div>

      <UAlert
        v-if="props.error"
        color="error"
        variant="soft"
        icon="i-lucide-circle-alert"
        title="明细读取失败"
        :description="props.error"
        role="alert"
      >
        <template #actions>
          <UButton label="重试" color="error" variant="soft" :loading="props.loading" @click="emit('retry')" />
        </template>
      </UAlert>

      <div v-else-if="props.loading && !props.data" class="statistics-drillover-loading" role="status" aria-label="正在读取统计明细">
        <USkeleton v-for="index in 5" :key="index" class="h-12 w-full" />
      </div>

      <UEmpty
        v-else-if="props.data && !props.data.items.length"
        icon="i-lucide-search-x"
        title="当前条件暂无明细"
        description="可以关闭抽屉后调整筛选范围。"
        variant="subtle"
      />

      <template v-else-if="props.data">
        <UCard variant="subtle" :ui="{ body: 'grid grid-cols-3 gap-3 p-4' }" aria-label="支出明细汇总">
          <div><span class="statistics-drillover-total-label">原支出</span><strong>{{ money(props.data.totals.originalAmountMinor) }}</strong></div>
          <div><span class="statistics-drillover-total-label">有效退款</span><strong>{{ money(props.data.totals.refundedAmountMinor) }}</strong></div>
          <div><span class="statistics-drillover-total-label">净支出</span><strong>{{ money(props.data.totals.netExpenseMinor) }}</strong></div>
        </UCard>

        <UTable
          :data="props.data.items"
          :columns="[
            { accessorKey: 'transaction', header: '交易' },
            { accessorKey: 'occurredAt', header: '发生时间' },
            { accessorKey: 'netExpenseMinor', header: '净支出' },
            { accessorKey: 'actions', header: '操作' },
          ]"
          caption="统计明细交易"
          :ui="{ td: 'align-middle' }"
        >
          <template #transaction-cell="{ row }">
            <span class="statistics-drillover-transaction">
              <strong>{{ row.original.transaction.description || '支出' }}</strong>
              <small>原支出 {{ money(row.original.originalAmountMinor) }} · 已退 {{ money(row.original.refundedAmountMinor) }}</small>
            </span>
          </template>
          <template #occurredAt-cell="{ row }">
            <time :datetime="row.original.transaction.occurredAt">{{ localInput(row.original.transaction.occurredAt).replace('T', ' ') }}</time>
          </template>
          <template #netExpenseMinor-cell="{ row }">
            <strong class="tabular-nums">{{ money(row.original.netExpenseMinor) }}</strong>
          </template>
          <template #actions-cell="{ row }">
            <UButton color="neutral" variant="ghost" size="sm" label="交易详情" @click="emit('openTransaction', row.original.transaction.id)" />
          </template>
        </UTable>
      </template>
    </template>
  </USlideover>
</template>

<style scoped>
.statistics-drillover-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.statistics-drillover-heading h2,
.statistics-drillover-heading p {
  margin: 0;
}

.statistics-drillover-loading {
  display: grid;
  gap: 12px;
}

.statistics-drillover-total-label {
  display: block;
  color: var(--ui-text-muted);
  font-size: 11px;
}

.statistics-drillover-total strong {
  display: block;
  margin-top: 4px;
  font-variant-numeric: tabular-nums;
}

.statistics-drillover-transaction {
  display: grid;
  min-width: 0;
  gap: 3px;
}

.statistics-drillover-transaction strong {
  overflow-wrap: anywhere;
}

.statistics-drillover-transaction small,
.statistics-drillover-transaction time {
  color: var(--ui-text-muted);
  font-size: 11px;
}

@media (max-width: 640px) {
  .statistics-drillover :deep(th:nth-child(2)),
  .statistics-drillover :deep(td:nth-child(2)) {
    display: none;
  }
}
</style>
