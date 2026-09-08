import { expect, test } from 'bun:test'
import { minor, localInput } from '../app/utils/money'
test('金额以整数分累计，拒绝无效或精度溢出输入', () => {
  expect(minor('0.10') + minor('0.20')).toBe(30)
  expect(minor('-12.3')).toBe(-1230)
  for (const value of ['NaN', 'Infinity', '1.005', '', '9007199254740992']) expect(() => minor(value)).toThrow()
})
test('本地表单时间转换后代表同一分钟', () => {
  const date = '2026-09-08T01:23:00Z'
  expect(new Date(localInput(date)).toISOString()).toBe('2026-09-08T01:23:00.000Z')
  expect(localInput('2026-09-08T01:23:00')).toBe(localInput(date))
})
