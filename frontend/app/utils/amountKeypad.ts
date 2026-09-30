import { minor } from './money'

export type AmountOperator = '+' | '-'
interface AmountTerm {
  value: string
  operator: AmountOperator
}
export interface AmountDraft {
  value: string
  terms: AmountTerm[]
  calculated: boolean
}

export function emptyAmountDraft(value = ''): AmountDraft {
  return { value, terms: [], calculated: false }
}

export function updateAmount(draft: AmountDraft, value: string): AmountDraft {
  return { ...draft, value, calculated: false }
}

export function appendAmount(draft: AmountDraft, key: string): AmountDraft {
  const value = draft.calculated ? '' : draft.value
  if (key === '.') {
    if (value.includes('.')) return draft
    return updateAmount(draft, `${value || '0'}.`)
  }
  if (!/^\d$/.test(key)) return draft
  if (value.includes('.') && value.split('.')[1]!.length >= 2) return draft
  return updateAmount(draft, value === '0' ? key : value + key)
}

export function deleteAmount(draft: AmountDraft): AmountDraft {
  if (!draft.value && draft.terms.length) {
    return { value: draft.terms.at(-1)!.value, terms: draft.terms.slice(0, -1), calculated: false }
  }
  return updateAmount(draft, draft.value.slice(0, -1))
}

export function setAmountOperator(draft: AmountDraft, operator: AmountOperator): AmountDraft {
  if (!draft.value && draft.terms.length) {
    return { ...draft, terms: [...draft.terms.slice(0, -1), { ...draft.terms.at(-1)!, operator }] }
  }
  if (!draft.value) throw new Error('请输入运算金额')
  minor(draft.value)
  // 记录操作数与运算符；此处不求和，也不显示中间结果。
  return { value: '', terms: [...draft.terms, { value: draft.value, operator }], calculated: false }
}

export function amountExpression(draft: AmountDraft): string {
  if (!draft.terms.length) return ''
  return [...draft.terms.map(term => `${term.value} ${term.operator}`), draft.value].join(' ').trim()
}

export function calculateAmount(draft: AmountDraft): AmountDraft {
  if (!draft.value) throw new Error('请输入运算金额')
  const values = [...draft.terms.map(term => minor(term.value)), minor(draft.value)]
  let result = values[0]!
  for (let index = 1; index < values.length; index++) {
    result = draft.terms[index - 1]!.operator === '+' ? result + values[index]! : result - values[index]!
    if (!Number.isSafeInteger(result)) throw new Error('金额超出可精确处理范围')
  }
  // 整数分直接格式化，避免大金额除以 100 时再次经过浮点舍入。
  const cents = BigInt(result)
  const absolute = cents < 0n ? -cents : cents
  const value = `${cents < 0n ? '-' : ''}${absolute / 100n}.${String(absolute % 100n).padStart(2, '0')}`
  return { ...emptyAmountDraft(value), calculated: true }
}
