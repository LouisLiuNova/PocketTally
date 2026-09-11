<script setup lang="ts">
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
</script>

<template>
  <div class="page-flow page-flow--accounts">
  <div class="section-intro">
    <div><p>账户合计余额</p><h2>{{ money(balance) }}</h2></div>
    <UButton label="新建账户" icon="i-lucide-plus" @click="workspace.resourceEditor.value = { kind: 'accounts' }" />
  </div>
  <p v-if="workspace.loaded.value && !workspace.accounts.value.length" class="empty-state">暂无账户，请先新建账户。</p>
  <UPageGrid as="div" class="page-grid account-card-grid">
    <article v-for="account in workspace.accounts.value" :key="account.id" class="balance-card">
      <span>{{ account.type === 'debit' ? '借记账户' : '信用账户' }}</span>
      <div class="card-brand">{{ account.name }}</div><strong>{{ money(minor(account.amount)) }}</strong>
      <small>{{ account.description || account.cardNumber || '余额来自有效交易' }}</small>
      <div>
        <button @click="workspace.transactionEditor.value = { accountId: account.id }">调账</button>
        <button @click="showAccountLedger(account.id)">流水</button>
        <button @click="workspace.resourceEditor.value = { kind: 'accounts', item: account }">编辑</button>
        <button class="danger" @click="workspace.deleteResource('accounts', account)">删除</button>
      </div>
    </article>
  </UPageGrid>
  </div>
</template>
