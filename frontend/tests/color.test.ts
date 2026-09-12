import { describe, expect, test } from 'bun:test'
import { colorValidationMessage, isValidHexColor } from '../app/utils/color'

describe('hex color validation', () => {
  test('accepts six-digit colors with either letter case', () => {
    expect(isValidHexColor('#005CAF')).toBe(true)
    expect(isValidHexColor('#abcdef')).toBe(true)
  })

  test('rejects empty, missing prefix, wrong length and non-hex values', () => {
    expect(isValidHexColor('')).toBe(false)
    expect(isValidHexColor('005CAF')).toBe(false)
    expect(isValidHexColor('#12345')).toBe(false)
    expect(isValidHexColor('#1234567')).toBe(false)
    expect(isValidHexColor('#12GG56')).toBe(false)
    expect(isValidHexColor('#123456 ')).toBe(false)
  })

  test('returns a field-level message for every invalid shape', () => {
    expect(colorValidationMessage('')).toContain('请输入')
    expect(colorValidationMessage('005CAF')).toContain('# 开头')
    expect(colorValidationMessage('#12345')).toContain('6 位')
    expect(colorValidationMessage('#12GG56')).toContain('十六进制')
  })
})
