<script setup lang="ts">
import { APP_ROUTES, appRoute } from '~/constants/navigation'
import { APPEARANCE_PALETTES } from '~/constants/appearance'
import { ledgerWorkspaceKey } from '~/composables/useLedgerWorkspace'
import { kindLabels } from '~/types/ledger'
import { localInput, money } from '~/utils/money'
import { accountNames, signedAmount } from '~/utils/transactionDisplay'

const route = useRoute()
const workspace = createLedgerWorkspace()
provide(ledgerWorkspaceKey, workspace)

const currentRoute = computed(() => appRoute(route.path))
const today = new Intl.DateTimeFormat('zh-CN', { dateStyle: 'full', timeZone: 'Asia/Shanghai' }).format(new Date())

useHead(() => ({ title: `PocketTally · ${currentRoute.value.title}` }))
</script>

<template>
  <UApp>
    <div class="app-shell">
      <aside class="sidebar">
        <div class="brand">
          <div class="brand-mark"><UIcon name="i-lucide-circle-dollar-sign" /></div>
          <span class="brand-label">PocketTally</span>
        </div>
        <nav aria-label="主导航">
          <NuxtLink
            v-for="item in APP_ROUTES"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="{ active: route.path === item.path }"
            :aria-label="item.label"
            :aria-current="route.path === item.path ? 'page' : undefined"
          >
            <UIcon :name="item.icon" />
            <span class="nav-label">{{ item.label }}</span>
          </NuxtLink>
        </nav>
        <div class="sidebar-foot"><p class="hint">个人账本 · CNY<br>统计边界 · Asia/Shanghai</p></div>
      </aside>

      <UMain class="app-main">
        <UContainer class="page-container" :ui="{ base: 'w-full max-w-[1580px] mx-auto px-4 sm:px-6 lg:px-8' }">
        <header class="topbar">
          <div><p class="eyebrow">{{ today }}</p><h1>{{ currentRoute.title }}</h1></div>
          <div class="top-actions">
            <UButton color="neutral" variant="ghost" icon="i-lucide-sun-moon" aria-label="外观设置" @click="workspace.showAppearance.value = !workspace.showAppearance.value" />
            <UButton color="neutral" variant="outline" label="刷新" :loading="workspace.loading.value" :aria-busy="workspace.loading.value" @click="workspace.refreshWorkspace" />
            <UButton icon="i-lucide-plus" label="记一笔" :disabled="!workspace.loaded.value || workspace.loading.value || !!workspace.loadError.value" @click="workspace.transactionEditor.value = {}" />
          </div>
        </header>

        <div v-if="workspace.showAppearance.value" class="view-toolbar">
          <label>主题 <select v-model="workspace.theme.value"><option value="system">跟随系统</option><option value="light">亮色</option><option value="dark">暗色</option></select></label>
          <label>配色 <select v-model="workspace.palette.value"><option v-for="item in APPEARANCE_PALETTES" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
        </div>
        <p v-if="workspace.notice.value" role="status" class="info-strip">{{ workspace.notice.value }}<button class="text-link" aria-label="关闭提示" @click="workspace.notice.value = ''">×</button></p>
        <div v-if="workspace.loadError.value || workspace.detailError.value" role="alert" class="error-box">
          {{ workspace.loadError.value || workspace.detailError.value }}
          {{ workspace.loaded.value && workspace.loadError.value ? '以下为上次成功读取的数据。' : '' }}
          <UButton label="重试" color="neutral" @click="workspace.refreshWorkspace" />
        </div>
        <p v-if="workspace.loading.value && !workspace.loaded.value" role="status" class="empty-state">正在从账本服务同步资源…</p>

          <NuxtPage />
        </UContainer>
      </UMain>
    </div>

    <UModal :open="!!workspace.transactionEditor.value" :dismissible="true" title="交易表单" @update:open="value => { if (!value) workspace.transactionEditor.value = null }">
      <template #content>
        <TransactionEditor
          v-if="workspace.transactionEditor.value"
          v-bind="workspace.transactionEditor.value"
          :accounts="workspace.accounts.value"
          :categories="workspace.categories.value"
          :tags="workspace.tags.value"
          :refund-summary="workspace.refundSummary.value"
          @close="workspace.transactionEditor.value = null"
          @saved="workspace.saved"
        />
      </template>
    </UModal>
    <UModal :open="!!workspace.resourceEditor.value" :dismissible="true" title="资源表单" @update:open="value => { if (!value) workspace.resourceEditor.value = null }">
      <template #content>
        <ResourceEditor
          v-if="workspace.resourceEditor.value"
          v-bind="workspace.resourceEditor.value"
          :categories="workspace.categories.value"
          @close="workspace.resourceEditor.value = null"
          @saved="workspace.saved"
        />
      </template>
    </UModal>
    <UModal :open="!!workspace.selected.value && !workspace.transactionEditor.value && !workspace.confirmation.value" title="交易详情" @update:open="value => { if (!value) workspace.selected.value = null }">
      <template #body>
        <template v-if="workspace.selected.value">
          <div class="detail-amount">{{ signedAmount(workspace.selected.value) }}<span class="status-dot">{{ workspace.selected.value.isVoid ? '已作废' : '有效' }}</span></div>
          <dl class="mvp-detail">
            <dt>类型</dt><dd>{{ kindLabels[workspace.selected.value.type] }}</dd>
            <dt>说明</dt><dd>{{ workspace.selected.value.description || '无' }}</dd>
            <dt>账户</dt><dd>{{ accountNames(workspace.selected.value) }}</dd>
            <dt>分类</dt><dd>{{ workspace.selected.value.category?.name || '不适用' }}</dd>
            <dt>发生时间</dt><dd>{{ localInput(workspace.selected.value.occurredAt).replace('T', ' ') }}（上海）</dd>
            <dt>标签</dt><dd>{{ workspace.selected.value.tags.map(tag => tag.name).join('、') || '无' }}</dd>
            <template v-if="workspace.selected.value.voidedAt"><dt>作废时间</dt><dd>{{ localInput(workspace.selected.value.voidedAt).replace('T', ' ') }}</dd></template>
          </dl>
          <p v-if="workspace.selected.value.type === 'expense'" class="info-strip">
            {{ workspace.refundLoading.value ? '正在读取退款额度…' : `已退 ${money(workspace.refundSummary.value?.refundedAmountMinor || 0)} · 剩余可退 ${money(workspace.refundSummary.value?.remainingRefundableAmountMinor || 0)}` }}
          </p>
          <button v-if="workspace.selected.value.refundOfTransactionId" class="text-link" @click="workspace.openTransaction(workspace.selected.value.refundOfTransactionId)">查看原支出 →</button>
          <div v-if="!workspace.selected.value.isVoid" class="composer-actions">
            <UButton label="编辑交易" color="neutral" @click="workspace.transactionEditor.value = { editing: workspace.selected.value }" />
            <UButton v-if="workspace.selected.value.type === 'expense'" label="申请退款" :disabled="workspace.refundLoading.value || !workspace.refundSummary.value?.canRefund" @click="workspace.transactionEditor.value = { refund: workspace.selected.value }" />
            <UButton label="作废交易" color="error" variant="soft" @click="workspace.voidSelected" />
          </div>
        </template>
      </template>
    </UModal>
    <UModal :open="!!workspace.confirmation.value" :dismissible="!workspace.busy.value" :title="workspace.confirmation.value?.title" @update:open="value => { if (!value && !workspace.busy.value) workspace.confirmation.value = null }">
      <template #body><p>{{ workspace.confirmation.value?.text }}</p><p v-if="workspace.actionError.value" role="alert" class="error-box">{{ workspace.actionError.value }}</p></template>
      <template #footer><UButton label="取消" color="neutral" :disabled="workspace.busy.value" @click="workspace.confirmation.value = null" /><UButton label="确认操作" color="error" :loading="workspace.busy.value" :aria-busy="workspace.busy.value" :disabled="workspace.busy.value" @click="workspace.confirmAction" /></template>
    </UModal>
  </UApp>
</template>
