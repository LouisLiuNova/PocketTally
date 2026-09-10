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
  const accounts = ref<Account[]>([])
  const categories = ref<Category[]>([])
  const tags = ref<Tag[]>([])
  const loading = ref(false)
  const loadError = ref('')
  const loaded = ref(false)
  let request: Promise<void> | null = null

  async function refreshResources() {
    if (request) return request
    loading.value = true
    loadError.value = ''
    request = Promise.all([
      $fetch<Account[]>('/api/v1/accounts'),
      $fetch<Category[]>('/api/v1/categories'),
      $fetch<Tag[]>('/api/v1/tags'),
    ]).then(([accountData, categoryData, tagData]) => {
      accounts.value = accountData
      categories.value = categoryData
      tags.value = tagData
      loaded.value = true
    }).catch((error) => {
      loadError.value = errorMessage(error)
      throw error
    }).finally(() => {
      loading.value = false
      request = null
    })
    return request
  }

  return { accounts, categories, tags, loading, loadError, loaded, refreshResources }
}
