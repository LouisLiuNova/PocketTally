import { describe, expect, test } from 'bun:test'
import { appendAmount, calculateAmount, deleteAmount, emptyAmountDraft } from '../app/utils/amountKeypad'

describe('快捷金额输入', () => {
  test('两位小数、删除和连续运算按整数分计算', () => {
    let draft = emptyAmountDraft()
    for (const key of ['1', '2', '.', '3', '4', '5']) draft = appendAmount(draft, key)
    expect(draft.value).toBe('12.34')
    draft = calculateAmount(draft, '+')
    draft = appendAmount(draft, '0')
    draft = appendAmount(draft, '.')
    draft = appendAmount(draft, '6')
    draft = calculateAmount(draft, '-')
    expect(draft.value).toBe('12.94')
    draft = appendAmount(draft, '2')
    expect(calculateAmount(draft, null).value).toBe('10.94')
    expect(deleteAmount(draft).value).toBe('')
  })

  test('连续运算符替换操作，非法精度和空操作数不能结算', () => {
    let draft = calculateAmount(emptyAmountDraft('5'), '+')
    draft = calculateAmount(draft, '-')
    expect(draft.operator).toBe('-')
    expect(() => calculateAmount(draft, null)).toThrow('请输入运算金额')
    expect(() => calculateAmount(emptyAmountDraft('1.234'), '+')).toThrow('金额最多保留两位小数')
    expect(calculateAmount(appendAmount(draft, '7'), null).value).toBe('-2')
  })
})
