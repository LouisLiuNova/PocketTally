import { minor } from './money'

export type AmountOperator = '+' | '-'
export interface AmountDraft {
  value: string
  accumulator: number | null
  operator: AmountOperator | null
  replaceNext: boolean
}

export function emptyAmountDraft(value = ''): AmountDraft {
  return { value, accumulator: null, operator: null, replaceNext: false }
}

export function appendAmount(draft: AmountDraft, key: string): AmountDraft {
  const value = draft.replaceNext ? '' : draft.value
  if (key === '.') {
    if (value.includes('.')) return draft
    return { ...draft, value: `${value || '0'}.`, replaceNext: false }
  }
  if (!/^\d$/.test(key)) return draft
  if (value.includes('.') && value.split('.')[1]!.length >= 2) return draft
  return { ...draft, value: value === '0' ? key : value + key, replaceNext: false }
}

export function deleteAmount(draft: AmountDraft): AmountDraft {
  return { ...draft, value: draft.replaceNext ? '' : draft.value.slice(0, -1), replaceNext: false }
}

export function calculateAmount(draft: AmountDraft, nextOperator: AmountOperator | null): AmountDraft {
  if (draft.replaceNext && draft.accumulator !== null) {
    if (!nextOperator) throw new Error('请输入运算金额')
    return { ...draft, operator: nextOperator }
  }
  const current = minor(draft.value)
  const result = draft.accumulator === null ? current : draft.operator === '+'
    ? draft.accumulator + current : draft.accumulator - current
  if (!Number.isSafeInteger(result)) throw new Error('金额超出可精确处理范围')
  const value = String(result / 100)
  return { value, accumulator: nextOperator ? result : null, operator: nextOperator, replaceNext: !!nextOperator }
}
