import { expect, test } from 'bun:test'
import { summarize } from '../app/utils/reports'
test('退款抵减支出，作废、调账和转账不计入收支', () => {
  expect(summarize([
    { type: 'income', amount: 100, isVoid: false },
    { type: 'expense', amount: 70, isVoid: false },
    { type: 'expense_refund', amount: 20, isVoid: false },
    { type: 'expense_refund', amount: 10, isVoid: true },
    { type: 'transfer', amount: 1000, isVoid: false },
    { type: 'balance_adjustment', amount: 1000, isVoid: false },
  ])).toEqual({ income: 10000, expense: 7000, refunds: 2000, net: 5000 })
})
test('当期仅有以前支出的退款时允许净支出为负', () => {
  expect(summarize([{ type: 'expense_refund', amount: 20, isVoid: false }]).net).toBe(-2000)
})
