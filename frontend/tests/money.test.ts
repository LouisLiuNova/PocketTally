import { expect, test } from 'bun:test'
import { minor, localInput, shanghaiIso } from '../app/utils/money'
test('金额以整数分累计，拒绝无效或精度溢出输入', () => {
  expect(minor('0.10') + minor('0.20')).toBe(30)
  expect(minor('-12.3')).toBe(-1230)
  for (const value of ['NaN', 'Infinity', '1.005', '', '9007199254740992']) expect(() => minor(value)).toThrow()
})
test('表单固定显示上海时间并可无损转换回 UTC', () => {
  const date = '2026-09-08T01:23:00Z'
  expect(localInput(date)).toBe('2026-09-08T09:23')
  expect(shanghaiIso(localInput(date))).toBe('2026-09-08T01:23:00.000Z')
  expect(localInput('2026-09-08T01:23:00')).toBe(localInput(date))
})
