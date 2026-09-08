import { expect, type APIRequestContext } from '@playwright/test'

type Resource = { id: string; name: string }

async function post<T>(request: APIRequestContext, path: string, data: unknown): Promise<T> {
  const response = await request.post(`http://127.0.0.1:8012/api/v1${path}`, { data })
  expect(response.ok(), `${path} 创建失败：${await response.text()}`).toBe(true)
  return response.json() as Promise<T>
}

export async function seedDesktopLedger(request: APIRequestContext) {
  const suffix = Date.now().toString()
  const longName = `桌面兼容性长名称-${suffix}-${'名称'.repeat(12)}`
  const wallet = await post<Resource>(request, '/accounts', { type: 'debit', name: `桌面钱包-${suffix}` })
  const bank = await post<Resource>(request, '/accounts', { type: 'debit', name: `备用账户-${suffix}` })
  const expense = await post<Resource>(request, '/categories', { name: longName, purpose: 'expense', iconColor: '#005CAF', iconName: 'i-lucide-folder' })
  const income = await post<Resource>(request, '/categories', { name: `工资分类-${suffix}`, purpose: 'income', iconColor: '#005CAF', iconName: 'i-lucide-folder' })
  const tag = await post<Resource>(request, '/tags', { name: `桌面标签-${suffix}`, color: '#005CAF' })
  const occurredAt = new Date().toISOString()

  await post(request, '/transactions', {
    type: 'balance_adjustment', sourceAccountId: wallet.id, amount: 10000,
    balanceAdjustmentDirection: 'increase', description: `期初余额-${suffix}`, occurredAt,
  })
  await post(request, '/transactions', {
    type: 'income', destinationAccountId: wallet.id, amount: 1000,
    categoryId: income.id, description: `长说明-${'说明'.repeat(20)}-${suffix}`, occurredAt,
  })
  const expenseTransaction = await post<{ id: string }>(request, '/transactions', {
    type: 'expense', sourceAccountId: wallet.id, amount: 80, categoryId: expense.id,
    tagIds: [tag.id], description: `可打开详情-${suffix}`, occurredAt,
  })
  await post(request, '/transactions/refunds', {
    refundOfTransactionId: expenseTransaction.id, amount: 20, description: `退款-${suffix}`, occurredAt,
  })
  await post(request, '/transactions', {
    type: 'transfer', sourceAccountId: wallet.id, destinationAccountId: bank.id,
    amount: 100, description: `转账-${suffix}`, occurredAt,
  })

  for (let index = 0; index < 21; index += 1) {
    await post(request, '/transactions', {
      type: 'expense', sourceAccountId: wallet.id, amount: 1 + index,
      categoryId: expense.id, tagIds: [tag.id], description: `分页交易-${suffix}-${index + 1}`, occurredAt,
    })
  }

  return { suffix, longName, wallet, bank, expense, income, tag, expenseTransaction }
}
