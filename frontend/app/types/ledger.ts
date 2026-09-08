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
export interface Page<T> { items: T[]; total: number; page: number; pageSize: number }
export interface RefundSummary {
  originalAmountMinor: number; refundedAmountMinor: number; remainingRefundableAmountMinor: number
  canRefund: boolean; activeRefundCount: number
}
export interface Period { startDate: string; endDate: string; timezone: 'Asia/Shanghai' }
export interface PeriodAmount { currentAmountMinor: number; previousAmountMinor: number; changeAmountMinor: number; changePercent: number | null }
export interface Overview { period: Period; previousPeriod: Period; income: PeriodAmount; netExpense: PeriodAmount; netCashFlow: PeriodAmount }
export interface CashFlowBucket { startAt: string; endAt: string; incomeAmountMinor: number; refundAmountMinor: number; expenseAmountMinor: number; netCashFlowMinor: number }
export interface CashFlow { period: Period; granularity: Granularity; buckets: CashFlowBucket[] }
export interface ExpenseBucket { startAt: string; endAt: string; netExpenseMinor: number; cumulativeNetExpenseMinor: number }
export interface Expenses { period: Period; granularity: Granularity; buckets: ExpenseBucket[]; cumulativeStartMinor: number }
export interface CategoryBucket { startAt: string; endAt: string; amountMinor: number }
export interface CategoryAmount {
  categoryId: string; name: string; purpose: 'expense'; amountMinor: number; directAmountMinor: number
  previousAmountMinor: number; changeAmountMinor: number; changeContributionMinor: number
  children: CategoryAmount[]; timeBuckets: CategoryBucket[]
}
export interface CategoryStatistics {
  period: Period; parentCategoryId: string | null; granularity: Granularity; items: CategoryAmount[]
  topCategories: CategoryAmount[]; other: { categoryIds: string[]; amounts: CategoryAmount[]; amountMinor: number }
  buckets: ExpenseBucket[]
}
export interface TagAmount { tagId: string; name: string; color: string; netExpenseMinor: number }
export interface TagStatistics { period: Period; items: TagAmount[] }
export interface CalendarDay { date: string; incomeAmountMinor: number; refundAmountMinor: number; expenseAmountMinor: number; netCashFlowMinor: number }
export interface CalendarStatistics { period: Period; month: string; days: CalendarDay[] }
export interface TransactionSummary { id: string; type: Kind; amount: number; description: string | null; occurredAt: string }
export interface ExpenseTransactionItem { transaction: TransactionSummary; originalAmountMinor: number; refundedAmountMinor: number; netExpenseMinor: number }
export interface ExpenseTransactionPage extends Page<ExpenseTransactionItem> {
  totals: { originalAmountMinor: number; refundedAmountMinor: number; netExpenseMinor: number }
}
export type Granularity = 'day' | 'week' | 'month'
export const kindLabels: Record<Kind, string> = { income: '收入', expense: '支出', transfer: '转账', balance_adjustment: '调账', expense_refund: '退款' }
