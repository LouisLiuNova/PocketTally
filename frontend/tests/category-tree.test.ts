import { describe, expect, test } from 'bun:test'
import { buildCategoryTree, filterCategoryTree, flattenVisibleCategoryTree } from '../app/utils/categoryTree'
import type { Category } from '../app/types/ledger'

function category(id: string, name: string, parentCategory: Category['parentCategory'] = null, purpose: Category['purpose'] = 'expense'): Category {
  return { id, name, purpose, parentCategory, iconColor: '#005CAF', iconName: 'i-lucide-folder', description: null }
}

describe('分类树', () => {
  test('按父分类 ID 构建多层树并保留完整路径', () => {
    const root = category('root', '餐饮')
    const child = category('child', '早餐', { id: root.id, name: root.name })
    const grandchild = category('grandchild', '豆浆', { id: child.id, name: child.name })
    const result = buildCategoryTree([grandchild, child, root], 'expense')

    expect(result.anomalies).toHaveLength(0)
    expect(result.roots[0].category.id).toBe('root')
    expect(result.roots[0].children[0].children[0].path).toBe('餐饮 / 早餐 / 豆浆')
  })

  test('循环和缺失父级进入异常区且不会递归崩溃', () => {
    const cycleA = category('a', '循环 A', { id: 'b', name: '循环 B' })
    const cycleB = category('b', '循环 B', { id: 'a', name: '循环 A' })
    const missing = category('missing', '旧分类', { id: 'gone', name: '已删除父级' })
    const result = buildCategoryTree([cycleA, cycleB, missing], 'expense')

    expect(result.roots).toHaveLength(0)
    expect(result.anomalies.map(item => item.reason)).toEqual(['层级存在循环', '层级存在循环', '父级不存在'])
  })

  test('搜索保留祖先，折叠状态控制键盘可见顺序', () => {
    const root = category('root', '生活')
    const child = category('child', '交通', { id: root.id, name: root.name })
    const tree = buildCategoryTree([root, child], 'expense')
    const filtered = filterCategoryTree(tree.roots, '交通')

    expect(filtered[0].category.id).toBe('root')
    expect(filtered[0].children[0].category.id).toBe('child')
    expect(flattenVisibleCategoryTree(tree.roots, new Set())).toHaveLength(1)
    expect(flattenVisibleCategoryTree(tree.roots, new Set(['root']))).toHaveLength(2)
  })
})
