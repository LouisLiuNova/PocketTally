import type { Transaction } from '~/types/ledger'
import { minor, money } from '~/utils/money'

export function accountNames(transaction: Transaction): string {
  return [transaction.sourceAccount?.name, transaction.destinationAccount?.name].filter(Boolean).join(' → ')
}

export function signedAmount(transaction: Transaction): string {
  const sign = transaction.type === 'income'
    || transaction.type === 'expense_refund'
    || (transaction.type === 'balance_adjustment' && transaction.balanceAdjustmentDirection === 'increase')
    ? '+'
    : transaction.type === 'transfer' ? '' : '−'
  return sign + money(minor(transaction.amount))
}
