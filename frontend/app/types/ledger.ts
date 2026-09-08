export type Kind = 'income' | 'expense' | 'transfer' | 'balance_adjustment' | 'expense_refund'
export interface Named { id: string; name: string }
export interface Account extends Named { type: 'debit' | 'credit'; amount: number; description: string | null; cardNumber: string | null }
export interface Category extends Named { purpose: 'income' | 'expense'; parentCategory: Named | null; iconColor: string; iconName: string; description: string | null }
export interface Tag extends Named { color: string; description: string | null }
export interface Transaction {
  id: string; type: Kind; amount: number; description: string | null
  sourceAccount: Named | null; destinationAccount: Named | null; category: Named | null
  tags: Tag[]; occurredAt: string; createdAt: string; updatedAt: string
  isVoid: boolean; voidedAt: string | null; refundOfTransactionId: string | null
  balanceAdjustmentDirection: 'increase' | 'decrease' | null
}
export const kindLabels: Record<Kind, string> = { income: '收入', expense: '支出', transfer: '转账', balance_adjustment: '调账', expense_refund: '退款' }
