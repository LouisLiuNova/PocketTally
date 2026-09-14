import { describe, expect, test } from 'bun:test'
import { CATEGORY_ICON_ITEMS, DEFAULT_CATEGORY_ICON } from '../app/constants/categoryIcons'

describe('分类图标目录', () => {
  test('数量、值和标签唯一，且使用合法的本地 Lucide 名称', () => {
    expect(CATEGORY_ICON_ITEMS.length).toBeGreaterThanOrEqual(40)
    expect(CATEGORY_ICON_ITEMS.length).toBeLessThanOrEqual(60)
    expect(new Set(CATEGORY_ICON_ITEMS.map(item => item.value)).size).toBe(CATEGORY_ICON_ITEMS.length)
    expect(new Set(CATEGORY_ICON_ITEMS.map(item => item.label)).size).toBe(CATEGORY_ICON_ITEMS.length)
    expect(CATEGORY_ICON_ITEMS.every(item => /^i-lucide-[a-z0-9-]+$/.test(item.value) && item.icon === item.value)).toBe(true)
    expect(CATEGORY_ICON_ITEMS.some(item => item.value === DEFAULT_CATEGORY_ICON)).toBe(false)
  })
})
