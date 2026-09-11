<script setup lang="ts">
import { zh_cn } from '@nuxt/ui/locale'
import { APP_ROUTES, appRoute } from '~/constants/navigation'
import type { ThemePreference } from '~/constants/appearance'
import { ledgerWorkspaceKey } from '~/composables/useLedgerWorkspace'
import { kindLabels } from '~/types/ledger'
import { localInput, money } from '~/utils/money'
import { accountNames, signedAmount } from '~/utils/transactionDisplay'

const route = useRoute()
const workspace = createLedgerWorkspace()
provide(ledgerWorkspaceKey, workspace)

const appLocale = {
  ...zh_cn,
  messages: {
    ...zh_cn.messages,
    dashboardSidebar: {
      title: '主导航',
      description: 'PocketTally 页面导航',
    },
  },
}

const currentRoute = computed(() => appRoute(route.path))
const themeModes: Array<{ value: ThemePreference; label: string; icon: string }> = [
  { value: 'system', label: '跟随系统', icon: 'i-lucide-monitor' },
  { value: 'light', label: '亮色', icon: 'i-lucide-sun' },
  { value: 'dark', label: '暗色', icon: 'i-lucide-moon' },
]
const currentThemeMode = computed(() => themeModes.find(mode => mode.value === workspace.theme.value) || themeModes[0])
const themeModeIndex = computed(() => Math.max(0, themeModes.findIndex(mode => mode.value === workspace.theme.value)))
const themeModeThumbClass = computed(() => `sidebar-theme-switch-thumb--${themeModeIndex.value}`)
const navigationItems = computed(() => APP_ROUTES.map(item => ({
  label: item.label,
  icon: item.icon,
  to: item.path,
  active: route.path === item.path,
  'aria-label': item.label,
})))
const breadcrumbItems = computed(() => currentRoute.value.path === '/'
  ? [{ label: currentRoute.value.breadcrumb, icon: currentRoute.value.icon }]
  : [
      { label: '总览', icon: APP_ROUTES[0].icon, to: '/', 'aria-label': '返回总览' },
      { label: currentRoute.value.breadcrumb, icon: currentRoute.value.icon },
    ])
const today = new Intl.DateTimeFormat('zh-CN', { dateStyle: 'full', timeZone: 'Asia/Shanghai' }).format(new Date())

useHead(() => ({ title: `PocketTally · ${currentRoute.value.title}` }))
</script>

<template>
  <UApp :locale="appLocale">
    <UDashboardGroup class="app-shell" storage="local" storage-key="pockettally-shell" unit="rem">
      <UDashboardSidebar
        id="primary"
        class="app-sidebar"
        collapsible
        resizable
        :default-size="15"
        :min-size="12"
        :max-size="20"
        :collapsed-size="4"
        :ui="{
          header: 'border-b border-default',
          body: 'gap-3',
          footer: 'border-t border-default',
          content: 'bg-default text-default sm:max-w-72',
        }"
      >
        <template #header="{ collapsed }">
          <NuxtLink v-if="!collapsed" to="/" class="shell-brand" aria-label="PocketTally 首页">
            <span class="shell-brand-mark" aria-hidden="true"><UIcon name="i-lucide-circle-dollar-sign" /></span>
            <span>PocketTally</span>
          </NuxtLink>
          <UTooltip :text="collapsed ? '展开主导航' : '折叠主导航'" :content="{ side: 'right' }">
            <UDashboardSidebarCollapse
              class="sidebar-collapse-button hidden lg:inline-flex"
              :class="collapsed ? 'mx-auto' : 'ml-auto'"
              :aria-label="collapsed ? '展开主导航' : '折叠主导航'"
            />
          </UTooltip>
        </template>

        <template #default="{ collapsed }">
          <div class="sidebar-main" :data-collapsed="collapsed">
            <UNavigationMenu
              aria-label="主导航"
              :items="navigationItems"
              orientation="vertical"
              color="primary"
              variant="pill"
              highlight
              :collapsed="collapsed"
              :tooltip="{ delayDuration: 0, content: { side: 'right' } }"
              :ui="{
                link: 'min-h-11 text-default hover:text-highlighted focus-visible:before:outline-[var(--pt-focus-ring)]',
                linkLeadingIcon: 'size-5 text-dimmed group-hover:text-default group-data-[active]:text-default',
              }"
            />
            <div class="sidebar-theme-control">
              <div class="sidebar-theme-switch-row">
                <UTooltip :text="`主题模式：${currentThemeMode.label}`" :delay-duration="0" :content="{ side: 'right' }">
                  <div class="sidebar-theme-switch" role="radiogroup" aria-label="主题模式">
                    <span class="sidebar-theme-switch-thumb" :class="themeModeThumbClass" aria-hidden="true" />
                    <button
                      v-for="mode in themeModes"
                      :key="mode.value"
                      class="sidebar-theme-switch-option"
                      type="button"
                      role="radio"
                      :aria-checked="workspace.theme.value === mode.value"
                      :aria-label="mode.label"
                      :title="mode.label"
                      @click="workspace.theme.value = mode.value"
                    >
                      <UIcon :name="mode.icon" aria-hidden="true" />
                    </button>
                  </div>
                </UTooltip>
              </div>
            </div>
          </div>
        </template>

        <template #footer="{ collapsed }">
          <div class="ledger-status" :data-collapsed="collapsed">
            <UTooltip text="个人账本" :delay-duration="0" :ignore-non-keyboard-focus="false" :content="{ side: 'right' }">
              <UButton class="ledger-status-item" color="neutral" variant="ghost" icon="i-lucide-book-open" :label="collapsed ? undefined : '个人账本'" aria-label="个人账本" />
            </UTooltip>
            <UTooltip text="货币：CNY" :delay-duration="0" :ignore-non-keyboard-focus="false" :content="{ side: 'right' }">
              <UButton class="ledger-status-item" color="neutral" variant="ghost" icon="i-lucide-circle-dollar-sign" :label="collapsed ? undefined : '货币：CNY'" aria-label="货币：CNY" />
            </UTooltip>
            <UTooltip text="统计边界：Asia/Shanghai" :delay-duration="0" :ignore-non-keyboard-focus="false" :content="{ side: 'right' }">
              <UButton class="ledger-status-item" color="neutral" variant="ghost" icon="i-lucide-clock-3" :label="collapsed ? undefined : '统计边界：Asia/Shanghai'" aria-label="统计边界：Asia/Shanghai" />
            </UTooltip>
          </div>
        </template>
      </UDashboardSidebar>

      <UDashboardPanel class="app-main">
        <template #header>
          <UDashboardNavbar :title="currentRoute.title" :ui="{ root: 'h-auto min-h-20 py-3', left: 'items-start', title: 'sr-only' }">
            <template #toggle>
              <UDashboardSidebarToggle aria-label="打开主导航" />
            </template>
            <template #left>
              <div class="min-w-0">
                <p class="eyebrow">{{ today }}</p>
                <h1>{{ currentRoute.title }}</h1>
                <UBreadcrumb :items="breadcrumbItems" class="mt-1" :ui="{ link: 'text-xs' }" />
              </div>
            </template>
            <template #right>
              <div class="top-actions">
                <UButton color="neutral" variant="outline" icon="i-lucide-refresh-cw" label="刷新" :loading="workspace.loading.value" :aria-busy="workspace.loading.value" @click="workspace.refreshWorkspace" />
                <UButton icon="i-lucide-plus" label="记一笔" :disabled="!workspace.loaded.value || workspace.loading.value || !!workspace.loadError.value" @click="workspace.transactionEditor.value = {}" />
              </div>
            </template>
          </UDashboardNavbar>
        </template>

        <template #body>
          <main>
            <UContainer class="page-container" :ui="{ base: 'w-full max-w-[1580px] mx-auto px-0' }">
            <p v-if="workspace.notice.value" role="status" class="info-strip">{{ workspace.notice.value }}<button class="text-link" aria-label="关闭提示" @click="workspace.notice.value = ''">×</button></p>
            <div v-if="workspace.loadError.value || workspace.detailError.value" role="alert" class="error-box">
              {{ workspace.loadError.value || workspace.detailError.value }}
              {{ workspace.loaded.value && workspace.loadError.value ? '以下为上次成功读取的数据。' : '' }}
              <UButton label="重试" color="neutral" @click="workspace.refreshWorkspace" />
            </div>
            <p v-if="workspace.loading.value && !workspace.loaded.value" role="status" class="empty-state">正在从账本服务同步资源…</p>

              <NuxtPage />
            </UContainer>
          </main>
        </template>
      </UDashboardPanel>
    </UDashboardGroup>

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
