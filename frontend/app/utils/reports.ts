import type { Transaction } from '../types/ledger'
import { minor } from './money'

export function summarize(transactions: Pick<Transaction, 'type' | 'amount' | 'isVoid'>[]) {
  let income = 0, expense = 0, refunds = 0
  for (const transaction of transactions) {
    if (transaction.isVoid) continue
    if (transaction.type === 'income') income += minor(transaction.amount)
    if (transaction.type === 'expense') expense += minor(transaction.amount)
    if (transaction.type === 'expense_refund') refunds += minor(transaction.amount)
  }
  return { income, expense, refunds, net: expense - refunds }
}
