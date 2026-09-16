import type { Account, Category, Granularity, Tag } from '~/types/ledger'

export function errorMessage(error: any): string {
  const data = error?.data
  if (data?.message) {
    const fields = Array.isArray(data.details) ? data.details.map((item: any) => item.msg).filter(Boolean).join('；') : ''
    return fields ? `${data.message}：${fields}` : data.message
  }
  return '无法连接账本服务，请检查服务后重试。'
}

export interface TransactionQuery {
  page: number
  pageSize: number
  startAt?: string
  endAt?: string
  type?: string
  accountId?: string
  categoryId?: string
  includeDescendants?: boolean
  tagId?: string
  q?: string
  status?: string
}

export interface StatisticsQuery {
  startDate: string
  endDate: string
  granularity: Granularity
  month: string
  parentCategoryId?: string
}

export function useLedger() {
  const requestFetch = useRequestFetch()
  const { data, pending, error, refresh } = useAsyncData('ledger-resources', async (_nuxtApp, { signal }) => {
    const [accounts, categories, tags] = await Promise.all([
      requestFetch<Account[]>('/api/v1/accounts', { signal }),
      requestFetch<Category[]>('/api/v1/categories', { signal }),
      requestFetch<Tag[]>('/api/v1/tags', { signal }),
    ])
    return { accounts, categories, tags }
  }, { lazy: true })

  const accounts = computed(() => data.value?.accounts || [])
  const categories = computed(() => data.value?.categories || [])
  const tags = computed(() => data.value?.tags || [])
  const loading = pending
  const loadError = computed(() => error.value ? errorMessage(error.value) : '')
  const loaded = computed(() => !!data.value)

  async function refreshResources() {
    await refresh({ dedupe: 'defer' })
    if (error.value) throw error.value
  }

  return { accounts, categories, tags, loading, loadError, loaded, refreshResources }
}
