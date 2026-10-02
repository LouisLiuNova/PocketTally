import { describe, expect, test } from 'bun:test'
import { amountExpression, appendAmount, calculateAmount, deleteAmount, emptyAmountDraft, parseAmountInput, setAmountOperator, updateAmount } from '../app/utils/amountKeypad'

describe('快捷金额输入', () => {
  test('金额框完整算式可编辑，结算前保留数字及运算符', () => {
    const draft = parseAmountInput('12.34 + 0.60 - 0.04')
    expect(amountExpression(draft)).toBe('12.34 + 0.60 - 0.04')
    expect(calculateAmount(draft).value).toBe('12.90')
    expect(amountExpression(parseAmountInput('12.34 +'))).toBe('12.34 +')
    expect(() => calculateAmount(parseAmountInput('12.34 +'))).toThrow('请输入运算金额')
    expect(calculateAmount(parseAmountInput('-2.00 + 3')).value).toBe('1.00')
    expect(calculateAmount(parseAmountInput('12.34 + 1.60 - 0.04')).value).toBe('13.90')
  })
  test('输入完整加减算式，只有等号结算且不显示中间结果', () => {
    let draft = emptyAmountDraft()
    for (const key of ['1', '2', '.', '3', '4', '5']) draft = appendAmount(draft, key)
    expect(draft.value).toBe('12.34')
    draft = setAmountOperator(draft, '+')
    draft = appendAmount(draft, '0')
    draft = appendAmount(draft, '.')
    draft = appendAmount(draft, '6')
    expect(amountExpression(draft)).toBe('12.34 + 0.6')
    draft = setAmountOperator(draft, '-')
    expect(draft.value).toBe('')
    expect(amountExpression(draft)).toBe('12.34 + 0.6 -')
    draft = appendAmount(draft, '2')
    expect(draft.value).toBe('2')
    const result = calculateAmount(draft)
    expect(result.value).toBe('10.94')
    expect(amountExpression(result)).toBe('')
    expect(deleteAmount(draft).value).toBe('')
    expect(appendAmount(result, '3').value).toBe('3')
    expect(calculateAmount(updateAmount(setAmountOperator(result, '+'), '0.06')).value).toBe('11.00')
  })

  test('连续运算符替换操作，非法精度和空操作数不能结算', () => {
    let draft = setAmountOperator(emptyAmountDraft('5'), '+')
    draft = setAmountOperator(draft, '-')
    expect(amountExpression(draft)).toBe('5 -')
    expect(() => calculateAmount(draft)).toThrow('请输入运算金额')
    expect(() => setAmountOperator(emptyAmountDraft('1.234'), '+')).toThrow('金额最多保留两位小数')
    expect(calculateAmount(appendAmount(draft, '7')).value).toBe('-2.00')
  })

  test('删除空操作数时返回上一个数字，清空移除完整算式', () => {
    const draft = setAmountOperator(updateAmount(setAmountOperator(emptyAmountDraft('12'), '+'), '3'), '-')
    const restored = deleteAmount(draft)
    expect(restored.value).toBe('3')
    expect(amountExpression(restored)).toBe('12 + 3')
    expect(deleteAmount(restored).value).toBe('')
    expect(emptyAmountDraft()).toEqual({ value: '', terms: [], calculated: false })
  })

  test('结算不修改原草稿，失败后可修正最后一个操作数', () => {
    const draft = updateAmount(setAmountOperator(emptyAmountDraft('12.34'), '+'), '0.60')
    expect(calculateAmount(draft).value).toBe('12.94')
    expect(amountExpression(draft)).toBe('12.34 + 0.60')
    const invalid = updateAmount(draft, '0.601')
    expect(() => calculateAmount(invalid)).toThrow('金额最多保留两位小数')
    expect(calculateAmount(deleteAmount(invalid)).value).toBe('12.94')
  })

  test('整数分边界保持精确，运算溢出明确报错', () => {
    expect(calculateAmount(emptyAmountDraft('90071992547409.91')).value).toBe('90071992547409.91')
    const draft = updateAmount(setAmountOperator(emptyAmountDraft('90071992547409.91'), '+'), '0.01')
    expect(() => calculateAmount(draft)).toThrow('金额超出可精确处理范围')
    expect(amountExpression(draft)).toBe('90071992547409.91 + 0.01')
  })
})
