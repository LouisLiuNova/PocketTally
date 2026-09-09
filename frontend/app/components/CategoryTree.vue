<script setup lang="ts">
import type { Category } from '~/types/ledger'
import { buildCategoryTree, filterCategoryTree, flattenVisibleCategoryTree, type CategoryTreeNode } from '~/utils/categoryTree'

const props = defineProps<{ categories: Category[] }>()
const emit = defineEmits<{
  create: [parentCategoryId?: string]
  edit: [category: Category]
  delete: [category: Category]
}>()

const purpose = ref<Category['purpose']>('expense')
const search = ref('')
const expandedIds = ref(new Set<string>())
const selectedId = ref('')
const focusedId = ref('')
const initialized = ref(false)
const previousSearchExpansion = ref<Set<string> | null>(null)
const tree = computed(() => buildCategoryTree(props.categories, purpose.value))
const filteredRoots = computed(() => filterCategoryTree(tree.value.roots, search.value))
const visibleNodes = computed(() => flattenVisibleCategoryTree(filteredRoots.value, expandedIds.value))
const selectedCategory = computed(() => props.categories.find(category => category.id === selectedId.value) || null)
const selectedNode = computed(() => visibleNodes.value.find(node => node.category.id === selectedId.value) || null)
const selectedChildren = computed(() => selectedCategory.value ? props.categories.filter(category => category.parentCategory?.id === selectedCategory.value?.id) : [])
const purposeLabel = computed(() => purpose.value === 'income' ? '收入' : '支出')

function allIds() { return new Set(props.categories.filter(category => category.purpose === purpose.value).map(category => category.id)) }
function parentId(category: Category) { return category.parentCategory?.id || '' }
function ancestors(category: Category) {
  const result: string[] = []; const seen = new Set<string>(); let current = category
  while (current.parentCategory && !seen.has(current.id)) {
    result.push(current.parentCategory.id); seen.add(current.id)
    const parent = props.categories.find(item => item.id === current.parentCategory?.id)
    if (!parent) break
    current = parent
  }
  return result
}
function selectCategory(category: Category) { selectedId.value = category.id; focusedId.value = category.id }
function toggle(category: Category) {
  const next = new Set(expandedIds.value)
  if (next.has(category.id)) next.delete(category.id); else next.add(category.id)
  expandedIds.value = next
}
function expandAll() { expandedIds.value = allIds() }
function collapseAll() { expandedIds.value = new Set() }
function filteredAncestorIds() {
  const query = search.value.trim().toLocaleLowerCase(); const ids = new Set<string>()
  if (!query) return ids
  for (const category of props.categories.filter(item => item.purpose === purpose.value)) {
    if (`${category.name} ${category.parentCategory?.name || ''}`.toLocaleLowerCase().includes(query)) ancestors(category).forEach(id => ids.add(id))
  }
  return ids
}
function handleSearch(value: string) {
  if (value && !search.value) previousSearchExpansion.value = new Set(expandedIds.value)
  search.value = value
  if (value) expandedIds.value = new Set([...expandedIds.value, ...filteredAncestorIds()])
  else if (previousSearchExpansion.value) { expandedIds.value = previousSearchExpansion.value; previousSearchExpansion.value = null }
}
function focusNode(node: CategoryTreeNode | undefined) {
  if (!node) return
  selectedId.value = node.category.id; focusedId.value = node.category.id
  nextTick(() => document.querySelector<HTMLElement>(`[data-category-id="${CSS.escape(node.category.id)}"]`)?.focus())
}
function handleKeydown(event: KeyboardEvent, node: CategoryTreeNode) {
  const index = visibleNodes.value.findIndex(item => item.category.id === node.category.id)
  if (event.key === 'ArrowDown') { event.preventDefault(); focusNode(visibleNodes.value[index + 1] || visibleNodes.value[0]) }
  else if (event.key === 'ArrowUp') { event.preventDefault(); focusNode(visibleNodes.value[index - 1] || visibleNodes.value.at(-1)) }
  else if (event.key === 'Home') { event.preventDefault(); focusNode(visibleNodes.value[0]) }
  else if (event.key === 'End') { event.preventDefault(); focusNode(visibleNodes.value.at(-1)) }
  else if (event.key === 'ArrowRight') { event.preventDefault(); if (node.children.length && !expandedIds.value.has(node.category.id)) toggle(node.category); else focusNode(node.children[0]) }
  else if (event.key === 'ArrowLeft') {
    event.preventDefault()
    if (expandedIds.value.has(node.category.id)) toggle(node.category)
    else focusNode(visibleNodes.value.find(item => item.children.some(child => child.category.id === node.category.id)))
  } else if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); selectCategory(node.category); if (node.children.length) toggle(node.category) }
}
function siblingPosition(node: CategoryTreeNode) {
  const siblings = props.categories.filter(category => category.purpose === purpose.value && parentId(category) === parentId(node.category))
  return { position: Math.max(1, siblings.findIndex(category => category.id === node.category.id) + 1), size: siblings.length }
}
function handlePurposeKeydown(event: KeyboardEvent, value: Category['purpose']) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  const values: Category['purpose'][] = ['expense', 'income']
  const index = values.indexOf(value)
  const nextIndex = event.key === 'Home' ? 0 : event.key === 'End' ? values.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + values.length) % values.length
  purpose.value = values[nextIndex]
  nextTick(() => document.querySelector<HTMLButtonElement>('[data-purpose="' + values[nextIndex] + '"]')?.focus())
}

watch(purpose, () => {
  search.value = ''; previousSearchExpansion.value = null
  const ids = allIds(); expandedIds.value = ids
  const first = tree.value.roots[0]?.category
  if (first) selectCategory(first)
})
watch(() => props.categories, (next, previous) => {
  const ids = new Set(next.map(category => category.id))
  if (!initialized.value) { expandedIds.value = new Set([...expandedIds.value, ...allIds()]); initialized.value = true }
  else expandedIds.value = new Set([...expandedIds.value].filter(id => ids.has(id)))
  const oldIds = new Set((previous || []).map(category => category.id))
  const newCategory = next.find(category => !oldIds.has(category.id) && category.purpose === purpose.value)
  const movedCategory = next.find(category => {
    const old = previous?.find(item => item.id === category.id)
    return old && parentId(old) !== parentId(category) && category.purpose === purpose.value
  })
  const changed = newCategory || movedCategory
  if (changed) {
    if (newCategory && newCategory.purpose !== purpose.value) purpose.value = newCategory.purpose
    const parent = parentId(changed)
    if (parent) expandedIds.value = new Set([...expandedIds.value, parent])
    selectedId.value = changed.id; focusedId.value = changed.id
    nextTick(() => document.querySelector<HTMLElement>(`[data-category-id="${CSS.escape(changed.id)}"]`)?.focus())
  } else if (!selectedCategory.value || selectedCategory.value.purpose !== purpose.value) {
    const first = tree.value.roots[0]?.category
    if (first) selectCategory(first)
  }
}, { deep: true, immediate: true })
watch(search, value => { if (value) expandedIds.value = new Set([...expandedIds.value, ...filteredAncestorIds()]) })
</script>

<template>
  <section class="category-workspace" aria-label="分类管理">
    <div class="taxonomy-tabs" role="tablist" aria-label="分类用途">
      <button v-for="item in [{ value: 'expense', label: '支出分类' }, { value: 'income', label: '收入分类' }]" :key="item.value" :data-purpose="item.value" role="tab" :tabindex="purpose === item.value ? 0 : -1" :aria-selected="purpose === item.value" :class="{ active: purpose === item.value }" @click="purpose = item.value as Category['purpose']" @keydown="handlePurposeKeydown($event, item.value as Category['purpose'])">{{ item.label }}<span>{{ props.categories.filter(category => category.purpose === item.value).length }}</span></button>
    </div>
    <div class="category-tree-layout">
      <article class="panel category-tree-panel">
        <div class="panel-head"><div><h2>分类结构</h2><p class="hint">使用真实父分类关系组织层级；点击名称查看详情。</p></div><UButton label="新建分类" icon="i-lucide-plus" @click="emit('create')" /></div>
        <div class="category-tree-toolbar"><input :value="search" aria-label="搜索分类" placeholder="搜索分类……" @input="handleSearch(($event.target as HTMLInputElement).value)"><button class="text-link" @click="expandAll">全部展开</button><button class="text-link" @click="collapseAll">全部折叠</button></div>
        <div v-if="!filteredRoots.length && !tree.anomalies.length" class="empty-state">暂无{{ purposeLabel }}分类，点击「新建分类」开始。</div>
        <div v-else class="category-tree" role="tree" :aria-label="`${purposeLabel}分类树`">
          <div v-for="node in visibleNodes" :key="node.category.id" class="category-tree-row resource-row" :class="{ selected: selectedId === node.category.id }" :style="{ '--depth': node.depth }">
            <div :data-category-id="node.category.id" class="category-tree-item" role="treeitem" :tabindex="focusedId === node.category.id ? 0 : -1" :aria-level="node.depth + 1" :aria-setsize="siblingPosition(node).size" :aria-posinset="siblingPosition(node).position" :aria-expanded="node.children.length ? expandedIds.has(node.category.id) : undefined" :aria-label="`${node.category.name}，${purposeLabel}分类${node.children.length ? `，${node.children.length} 个子分类` : ''}`" @click="selectCategory(node.category)" @keydown="handleKeydown($event, node)">
              <button class="tree-toggle" :aria-label="node.children.length ? `${expandedIds.has(node.category.id) ? '折叠' : '展开'}${node.category.name}` : `${node.category.name}没有子分类`" :disabled="!node.children.length" @click.stop="node.children.length && toggle(node.category)">{{ node.children.length ? (expandedIds.has(node.category.id) ? '▾' : '▸') : '·' }}</button>
              <span class="tree-branch" aria-hidden="true">{{ node.depth ? '└─' : '' }}</span><span class="category-icon" :style="{ color: node.category.iconColor, backgroundColor: `${node.category.iconColor}22` }"><UIcon :name="node.category.iconName || 'i-lucide-folder'" /></span>
              <span class="category-tree-name"><strong>{{ node.category.name }}</strong><small>{{ purposeLabel }}<template v-if="node.children.length"> · {{ node.children.length }} 个子分类</template><template v-if="node.category.parentCategory"> · 上级：{{ node.category.parentCategory.name }}</template></small></span>
            </div>
            <div class="category-row-actions"><button class="text-link" :title="`为${node.category.name}新建子分类`" @click.stop="emit('create', node.category.id)">新建子分类</button><button class="text-link" :title="`编辑${node.category.name}`" @click.stop="emit('edit', node.category)">编辑</button><button class="text-link danger" :title="`删除${node.category.name}`" @click.stop="emit('delete', node.category)">删除</button></div>
          </div>
        </div>
        <section v-if="tree.anomalies.length" class="category-anomalies" aria-label="需要修复的分类">
          <h3>⚠ 有分类存在层级异常</h3><p class="hint">异常节点仍保留在这里，修复父分类后会回到正常树中。</p>
          <div v-for="item in tree.anomalies" :key="item.category.id" class="anomaly-row"><span><strong>{{ item.category.name }}</strong><small>{{ item.reason }}<template v-if="item.category.parentCategory"> · 父级：{{ item.category.parentCategory.name }}</template></small></span><button class="text-link" :title="`编辑${item.category.name}`" @click="emit('edit', item.category)">编辑</button></div>
        </section>
      </article>
      <aside class="panel category-inspector" aria-label="分类详情">
        <div v-if="selectedCategory"><div class="panel-head"><div><p class="eyebrow">{{ purposeLabel }}分类</p><h2>分类详情</h2><p class="category-inspector-title">当前分类：{{ selectedCategory.name }}</p></div><span class="category-inspector-icon" :style="{ color: selectedCategory.iconColor, backgroundColor: `${selectedCategory.iconColor}22` }"><UIcon :name="selectedCategory.iconName || 'i-lucide-folder'" /></span></div><dl class="category-detail"><dt>用途</dt><dd>用途：{{ purposeLabel }}</dd><dt>路径</dt><dd>路径：{{ selectedNode?.path || selectedCategory.name }}</dd><dt>父分类</dt><dd>父分类：{{ selectedCategory.parentCategory?.name || '顶级分类' }}</dd><dt>子分类</dt><dd>子分类：{{ selectedChildren.length }} 个</dd><dt>说明</dt><dd>说明：{{ selectedCategory.description || '无' }}</dd></dl><div class="composer-actions"><UButton label="编辑分类" color="neutral" icon="i-lucide-pencil" @click="emit('edit', selectedCategory)" /><UButton label="新建子分类" icon="i-lucide-plus" @click="emit('create', selectedCategory.id)" /><UButton label="删除" color="error" variant="soft" @click="emit('delete', selectedCategory)" /></div></div><p v-else class="empty-state">选择一个分类查看详情。</p>
      </aside>
    </div>
  </section>
</template>
