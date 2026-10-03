export type ImportStatus = 'ready' | 'needs_account' | 'needs_category' | 'duplicate' | 'skipped' | 'unsupported' | 'refund_pending' | 'imported'
export const importStatusLabels: Record<ImportStatus, string> = {
  ready: '可导入', needs_account: '待补账户', needs_category: '待补分类', duplicate: '重复', skipped: '已跳过', unsupported: '不支持', refund_pending: '退款待处理', imported: '已导入',
}
export interface ImportSourceFields {
  sourceId: string; merchantOrderId: string; counterparty: string; product: string; paymentMethod: string
  platformCategory: string; platformStatus: string; direction: string; amount: string; occurredAt: string; rowNumbers: number[]
}
export interface ImportRow {
  id: string; rowNumber: number; sourceId: string; status: ImportStatus; reason: string | null
  included: boolean; editable: boolean; type: 'income' | 'expense' | null; amountMinor: number; occurredAt: string | null
  description: string; paymentKey: string; accountId: string | null; categoryId: string | null
  transactionId: string | null; duplicateBatchId: string | null; original: ImportSourceFields; similarTransactionIds: string[]
}
export interface ImportSummary {
  inputRows: number; counts: Partial<Record<ImportStatus, number>>; selectedCount: number; unresolvedCount: number
  incomeMinor: number; expenseMinor: number; excludedMinor: number
  source: { inputRows: number; parseCounts: Record<string, number>; sourceAmountMinor: Record<string, number>; startAt: string | null; endAt: string | null }
}
export interface ImportBatch {
  id: string; provider: 'alipay' | 'wechat'; filename: string; sha256: string; parserVersion: string
  status: 'draft' | 'committed'; version: number; createdAt: string; updatedAt: string; committedAt: string | null
  summary: ImportSummary; paymentKeys: string[]; items: ImportRow[]; total: number; page: number; pageSize: number
}
export interface ImportHistory {
  items: { id: string; provider: 'alipay' | 'wechat'; filename: string; status: 'draft' | 'committed'; version: number; createdAt: string; committedAt: string | null; inputRows: number }[]
  total: number; page: number; pageSize: number
}
export interface ImportChange {
  rowIds?: string[]; paymentKey?: string; type?: 'income' | 'expense'; accountId?: string | null; categoryId?: string | null
  included?: boolean; amountMinor?: number; occurredAt?: string; description?: string; rememberMapping?: boolean; matchType?: 'income' | 'expense'
}
