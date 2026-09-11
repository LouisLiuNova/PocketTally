import { describe, expect, test } from 'bun:test'
import {
  APPEARANCE_PALETTES,
  DEFAULT_APPEARANCE,
  PALETTE_NAMES,
  parseAppearance,
  parseStoredAppearance,
} from '../app/constants/appearance'

describe('外观偏好契约', () => {
  test('八套配色的值、标签、种子和描述保持完整', () => {
    expect(APPEARANCE_PALETTES).toHaveLength(8)
    expect(APPEARANCE_PALETTES.map(item => item.value)).toEqual([...PALETTE_NAMES])
    expect(new Set(APPEARANCE_PALETTES.map(item => item.label)).size).toBe(8)
    expect(APPEARANCE_PALETTES.every(item => /^#[0-9A-F]{6}$/.test(item.seed))).toBe(true)
    expect(APPEARANCE_PALETTES.every(item => item.description.length > 0)).toBe(true)
  })

  test('兼容读取已有和新增配色', () => {
    expect(parseStoredAppearance('{"theme":"dark","palette":"fuji"}')).toEqual({ theme: 'dark', palette: 'fuji' })
    expect(parseStoredAppearance('{"theme":"light","palette":"yamabuki"}')).toEqual({ theme: 'light', palette: 'yamabuki' })
    expect(parseStoredAppearance('{"theme":"system","palette":"kurumi"}')).toEqual({ theme: 'system', palette: 'kurumi' })
  })

  test('损坏或未知字段分别回退，不丢弃另一个有效字段', () => {
    expect(parseStoredAppearance('not-json')).toEqual(DEFAULT_APPEARANCE)
    expect(parseAppearance({ theme: 'sepia', palette: 'asagi' })).toEqual({ theme: 'system', palette: 'asagi' })
    expect(parseAppearance({ theme: 'dark', palette: 'unknown' })).toEqual({ theme: 'dark', palette: 'ruri' })
    expect(parseAppearance(null)).toEqual(DEFAULT_APPEARANCE)
  })
})
