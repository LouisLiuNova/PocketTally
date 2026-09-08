import type { Category } from '../types/ledger'

export interface CategoryTreeNode {
  category: Category
  children: CategoryTreeNode[]
  depth: number
  path: string
}

export interface CategoryTreeAnomaly {
  category: Category
  reason: string
}

export interface CategoryTreeResult {
  roots: CategoryTreeNode[]
  anomalies: CategoryTreeAnomaly[]
}

const MAX_CATEGORY_DEPTH = 100

function parentId(category: Category): string | null { return category.parentCategory?.id || null }

function categoryPath(category: Category, byId: Map<string, Category>): string {
  const names: string[] = []
  const seen = new Set<string>()
  let current: Category | undefined = category
  while (current && !seen.has(current.id) && names.length <= MAX_CATEGORY_DEPTH) {
    names.unshift(current.name); seen.add(current.id)
    const id = parentId(current); current = id ? byId.get(id) : undefined
  }
  return names.join(' / ')
}

function invalidReason(category: Category, byId: Map<string, Category>): string | null {
  const seen = new Set<string>(); let current: Category | undefined = category; let depth = 0
  while (current) {
    if (seen.has(current.id)) return '层级存在循环'
    if (depth >= MAX_CATEGORY_DEPTH) return '层级过深'
    seen.add(current.id)
    const id = parentId(current)
    if (!id) return null
    const parent = byId.get(id)
    if (!parent) return '父级不存在'
    if (parent.purpose !== category.purpose) return '父级用途不一致'
    current = parent; depth += 1
  }
  return null
}

function makeNode(category: Category, byId: Map<string, Category>): CategoryTreeNode {
  return { category, children: [], depth: 0, path: categoryPath(category, byId) }
}

/**
 * 按分类 ID 建立指定用途的树，并隔离循环、缺失父级和异常深度。
 *
 * Args:
 *   categories: 服务端返回的分类列表。
 *   purpose: 需要构建的分类用途。
 *
 * Returns:
 *   正常树根和可供修复的异常分类。
 */
export function buildCategoryTree(categories: Category[], purpose: Category['purpose']): CategoryTreeResult {
  const byId = new Map(categories.map(category => [category.id, category]))
  const scoped = categories.filter(category => category.purpose === purpose)
  const anomalies = scoped.flatMap(category => {
    const reason = invalidReason(category, byId)
    return reason ? [{ category, reason }] : []
  })
  const anomalyIds = new Set(anomalies.map(item => item.category.id))
  const nodes = new Map<string, CategoryTreeNode>()
  for (const category of scoped) if (!anomalyIds.has(category.id)) nodes.set(category.id, makeNode(category, byId))
  const roots: CategoryTreeNode[] = []
  for (const category of scoped) {
    const node = nodes.get(category.id); if (!node) continue
    const parent = parentId(category) ? nodes.get(parentId(category)!) : undefined
    if (parent) parent.children.push(node); else roots.push(node)
  }
  const updateDepth = (node: CategoryTreeNode, depth: number) => { node.depth = depth; node.children.forEach(child => updateDepth(child, depth + 1)) }
  roots.forEach(root => updateDepth(root, 0))
  return { roots, anomalies }
}

/**
 * 保留匹配节点及其祖先，确保深层分类仍可定位。
 */
export function filterCategoryTree(roots: CategoryTreeNode[], query: string): CategoryTreeNode[] {
  const normalized = query.trim().toLocaleLowerCase()
  if (!normalized) return roots
  const filter = (node: CategoryTreeNode): CategoryTreeNode | null => {
    const children = node.children.map(filter).filter((item): item is CategoryTreeNode => !!item)
    const matched = `${node.category.name} ${node.path}`.toLocaleLowerCase().includes(normalized)
    return matched || children.length ? { ...node, children } : null
  }
  return roots.map(filter).filter((item): item is CategoryTreeNode => !!item)
}

/**
 * 返回当前展开状态下供键盘导航使用的节点顺序。
 */
export function flattenVisibleCategoryTree(roots: CategoryTreeNode[], expandedIds: Set<string>): CategoryTreeNode[] {
  const result: CategoryTreeNode[] = []
  const visit = (node: CategoryTreeNode) => { result.push(node); if (expandedIds.has(node.category.id)) node.children.forEach(visit) }
  roots.forEach(visit)
  return result
}
