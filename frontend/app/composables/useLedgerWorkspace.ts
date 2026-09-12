import type { InjectionKey } from 'vue'
import type { Account, Category, RefundSummary, Tag, Transaction } from '~/types/ledger'
import { errorMessage } from '~/composables/useLedger'
import { useAppMessages } from '~/composables/useAppMessages'
import {
  APPEARANCE_STORAGE_KEY,
  parseStoredAppearance,
  type PaletteName,
  type ThemePreference,
} from '~/constants/appearance'

export function createLedgerWorkspace() {
  const ledger = useLedger()
  const messages = useAppMessages()
  const selected = ref<Transaction | null>(null)
  const refundSummary = ref<RefundSummary | null>(null)
  const refundLoading = ref(false)
  const refundError = ref('')
  const transactionEditor = ref<{ editing?: Transaction; refund?: Transaction; accountId?: string } | null>(null)
  const editorBusy = ref(false)
  const resourceEditor = ref<{ kind: 'accounts' | 'categories' | 'tags'; item?: Account | Category | Tag; initialParentCategoryId?: string } | null>(null)
  const confirmation = ref<{ title: string; text: string; path: string; method: 'POST' | 'DELETE' } | null>(null)
  const actionError = ref('')
  const busy = ref(false)
  const refreshRevision = ref(0)
  const colorMode = useColorMode()
  const theme = ref<ThemePreference>('system')
  const palette = ref<PaletteName>('ruri')
  const resourceSyncMessageId = 'workspace-resource-sync'

  async function syncResources() {
    try {
      await ledger.refreshResources()
      messages.dismiss(resourceSyncMessageId)
      return true
    } catch {
      const description = ledger.loaded.value
        ? `${ledger.loadError.value} 以下为上次成功读取的数据。`
        : ledger.loadError.value
      messages.push({
        id: resourceSyncMessageId,
        level: 'error',
        title: '账本服务同步失败',
        description,
        action: { label: '重试', onSelect: () => void refreshWorkspace() },
      })
      return false
    }
  }

  async function refreshWorkspace() {
    const refreshed = await syncResources()
    if (refreshed) refreshRevision.value++
    return refreshed
  }

  async function saved() {
    const selectedId = selected.value?.id
    transactionEditor.value = null
    resourceEditor.value = null
    messages.push({ id: 'operation-saved', level: 'success', title: '保存成功', description: '已保存到本地账本。' })
    await refreshWorkspace()
    if (selectedId) await openTransaction(selectedId)
  }

  async function openTransaction(transaction: Transaction | string) {
    const transactionId = typeof transaction === 'string' ? transaction : transaction.id
    refundSummary.value = null
    refundError.value = ''
    refundLoading.value = false
    try {
      selected.value = typeof transaction === 'string'
        ? await $fetch<Transaction>(`/api/v1/transactions/${transaction}`)
        : transaction
      messages.dismiss(`transaction-detail-${transactionId}`)
      if (selected.value.type === 'expense') {
        refundLoading.value = true
        try {
          refundSummary.value = await $fetch<RefundSummary>(`/api/v1/transactions/${selected.value.id}/refund-summary`)
        } catch (error) {
          refundError.value = errorMessage(error)
        } finally {
          refundLoading.value = false
        }
      }
    } catch (error) {
      selected.value = null
      messages.push({
        id: `transaction-detail-${transactionId}`,
        level: 'error',
        title: '交易详情读取失败',
        description: errorMessage(error),
        action: { label: '重试', onSelect: () => void openTransaction(transactionId) },
      })
    }
  }

  async function retryRefundSummary() {
    if (!selected.value || selected.value.type !== 'expense') return
    refundLoading.value = true
    refundError.value = ''
    try {
      refundSummary.value = await $fetch<RefundSummary>(`/api/v1/transactions/${selected.value.id}/refund-summary`)
    } catch (error) {
      refundError.value = errorMessage(error)
    } finally {
      refundLoading.value = false
    }
  }

  function deleteResource(kind: 'accounts' | 'categories' | 'tags', item: Account | Category | Tag) {
    actionError.value = ''
    confirmation.value = {
      title: `删除「${item.name}」`,
      text: '仅未被引用的资源可以删除。有关联交易或子分类时，账本会保留资源并提示原因。',
      path: `/api/v1/${kind}/${item.id}`,
      method: 'DELETE',
    }
  }

  function createCategory(parentCategoryId?: string) {
    resourceEditor.value = { kind: 'categories', initialParentCategoryId: parentCategoryId }
  }

  function voidSelected() {
    if (!selected.value) return
    actionError.value = ''
    confirmation.value = {
      title: '作废这笔交易',
      text: '作废后撤销余额影响并保留审计记录。有有效退款的支出须先作废退款。',
      path: `/api/v1/transactions/${selected.value.id}/void`,
      method: 'POST',
    }
  }

  async function confirmAction() {
    if (!confirmation.value || busy.value) return
    busy.value = true
    actionError.value = ''
    try {
      await $fetch(confirmation.value.path, { method: confirmation.value.method, retry: 0 })
      confirmation.value = null
      messages.push({ id: 'operation-success', level: 'success', title: '操作成功', description: '账本操作已完成。' })
      await refreshWorkspace()
      if (selected.value) await openTransaction(selected.value.id)
    } catch (error) {
      actionError.value = errorMessage(error)
    } finally {
      busy.value = false
    }
  }

  function applyAppearance() {
    document.documentElement.dataset.palette = palette.value
    colorMode.preference = theme.value
    document.documentElement.dataset.theme = colorMode.value
    document.documentElement.style.colorScheme = colorMode.value
    try {
      localStorage.setItem(APPEARANCE_STORAGE_KEY, JSON.stringify({ theme: theme.value, palette: palette.value }))
    } catch {
      // 隐私模式仍允许切换外观。
    }
  }

  watch([theme, palette], () => {
    if (import.meta.client) applyAppearance()
  })
  watch(() => colorMode.value, (value) => {
    if (!import.meta.client) return
    document.documentElement.dataset.theme = value
    document.documentElement.style.colorScheme = value
  })

  onMounted(() => {
    let savedAppearance = parseStoredAppearance(null)
    try {
      savedAppearance = parseStoredAppearance(localStorage.getItem(APPEARANCE_STORAGE_KEY))
    } catch {
      // 隐私模式仍允许使用默认外观。
    }
    theme.value = savedAppearance.theme
    palette.value = savedAppearance.palette
    applyAppearance()
    void syncResources()
  })

  return {
    ...ledger,
    selected,
    refundSummary,
    refundLoading,
    refundError,
    transactionEditor,
    editorBusy,
    resourceEditor,
    confirmation,
    actionError,
    busy,
    refreshRevision,
    theme,
    palette,
    refreshWorkspace,
    saved,
    openTransaction,
    retryRefundSummary,
    deleteResource,
    createCategory,
    voidSelected,
    confirmAction,
  }
}

export type LedgerWorkspace = ReturnType<typeof createLedgerWorkspace>
export const ledgerWorkspaceKey: InjectionKey<LedgerWorkspace> = Symbol('ledger-workspace')

export function useLedgerWorkspace(): LedgerWorkspace {
  const workspace = inject(ledgerWorkspaceKey)
  if (!workspace) throw new Error('Ledger workspace is unavailable')
  return workspace
}
