import type { Account, Category, Tag, Transaction } from '~/types/ledger'

export function errorMessage(error: any): string {
  const data = error?.data
  if (data?.message) {
    const fields = Array.isArray(data.details) ? data.details.map((item: any) => item.msg).filter(Boolean).join('；') : ''
    return fields ? `${data.message}：${fields}` : data.message
  }
  return '无法连接账本服务，请检查服务后重试。'
}

export function useLedger() {
  const accounts = ref<Account[]>([])
  const categories = ref<Category[]>([])
  const tags = ref<Tag[]>([])
  const transactions = ref<Transaction[]>([])
  const loading = ref(false)
  const loadError = ref('')
  const loaded = ref(false)
  async function refresh() {
    if (loading.value) return
    loading.value = true
    loadError.value = ''
    try {
      const [a, c, t, tx] = await Promise.all([
        $fetch<Account[]>('/api/v1/accounts'), $fetch<Category[]>('/api/v1/categories'),
        $fetch<Tag[]>('/api/v1/tags'), $fetch<Transaction[]>('/api/v1/transactions', { query: { includeVoided: true } }),
      ])
      accounts.value = a; categories.value = c; tags.value = t; transactions.value = tx
      loaded.value = true
    } catch (error) { loadError.value = errorMessage(error) }
    finally { loading.value = false }
  }
  return { accounts, categories, tags, transactions, loading, loadError, loaded, refresh }
}
