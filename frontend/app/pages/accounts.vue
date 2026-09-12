<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { Account } from '~/types/ledger'
import { defaultTransactionState, compactQuery, serializeTransactionState } from '~/utils/routeQuery'
import { localInput, minor, money } from '~/utils/money'

const workspace = useLedgerWorkspace()
const today = localInput().slice(0, 10)
const balance = computed(() => workspace.accounts.value.reduce((sum, account) => sum + minor(account.amount), 0))

function showAccountLedger(accountId: string) {
  const state = defaultTransactionState(today)
  state.accountId = accountId
  return navigateTo({ path: '/transactions', query: compactQuery(serializeTransactionState(state, today)) })
}

function accountActions(account: Account): DropdownMenuItem[][] {
  return [
    [{
      label: '编辑',
      icon: 'i-lucide-pencil',
      onSelect: () => { workspace.resourceEditor.value = { kind: 'accounts', item: account } },
    }],
    [{
      label: '删除',
      icon: 'i-lucide-trash-2',
      color: 'error',
      onSelect: () => workspace.deleteResource('accounts', account),
    }],
  ]
}
</script>

<template>
  <div class="page-flow page-flow--accounts">
    <UCard class="account-summary-card" variant="outline">
      <div class="flex flex-wrap items-end justify-between gap-4">
        <div class="min-w-0">
          <p class="text-sm text-muted">账户合计余额</p>
          <h2 class="mt-1 text-3xl font-semibold tabular-nums">{{ money(balance) }}</h2>
        </div>
        <UButton label="新建账户" icon="i-lucide-plus" @click="workspace.resourceEditor.value = { kind: 'accounts' }" />
      </div>
    </UCard>

    <UEmpty
      v-if="workspace.loaded.value && !workspace.accounts.value.length"
      icon="i-lucide-wallet-cards"
      title="暂无账户"
      description="新建账户后，可以通过调账录入现有余额。"
    />

    <UPageGrid v-else as="div" class="page-grid account-card-grid">
      <UCard
        v-for="account in workspace.accounts.value"
        :key="account.id"
        :data-account-id="account.id"
        class="account-resource-card"
        variant="outline"
        :ui="{ root: 'h-full', body: 'flex h-full flex-col gap-3', footer: 'flex flex-wrap items-center gap-2' }"
      >
        <template #header>
          <div class="flex min-w-0 items-center justify-between gap-3">
            <h3 class="truncate font-semibold">{{ account.name }}</h3>
            <UBadge color="neutral" variant="soft" size="sm">
              {{ account.type === 'debit' ? '借记账户' : '信用账户' }}
            </UBadge>
          </div>
        </template>

        <strong class="text-3xl font-semibold tabular-nums">{{ money(minor(account.amount)) }}</strong>
        <p class="min-h-10 text-sm text-muted">{{ account.description || account.cardNumber || '余额来自有效交易' }}</p>

        <template #footer>
          <UButton color="neutral" variant="outline" icon="i-lucide-receipt-text" label="流水" @click="showAccountLedger(account.id)" />
          <UButton color="neutral" variant="soft" icon="i-lucide-scale" label="调账" @click="workspace.transactionEditor.value = { accountId: account.id }" />
          <UDropdownMenu :items="accountActions(account)" :content="{ align: 'end' }">
            <UButton
              class="ml-auto"
              color="neutral"
              variant="ghost"
              icon="i-lucide-ellipsis"
              square
              :aria-label="`更多操作：${account.name}`"
            />
          </UDropdownMenu>
        </template>
      </UCard>
    </UPageGrid>
  </div>
</template>
