<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { Category } from '~/types/ledger'
import { buildCategoryTree, filterCategoryTree, flattenVisibleCategoryTree, type CategoryTreeNode } from '~/utils/categoryTree'

const props = defineProps<{ categories: Category[]; purpose: Category['purpose'] }>()
const emit = defineEmits<{
  create: [parentCategoryId?: string]
  edit: [category: Category]
  delete: [category: Category]
}>()

const search = ref('')
const expandedIds = ref(new Set<string>())
const selectedId = ref('')
const focusedId = ref('')
const initialized = ref(false)
const previousSearchExpansion = ref<Set<string> | null>(null)
const tree = computed(() => buildCategoryTree(props.categories, props.purpose))
const filteredRoots = computed(() => filterCategoryTree(tree.value.roots, search.value))
const visibleNodes = computed(() => flattenVisibleCategoryTree(filteredRoots.value, expandedIds.value))
const selectedCategory = computed(() => props.categories.find(category => category.id === selectedId.value) || null)
const selectedNode = computed(() => visibleNodes.value.find(node => node.category.id === selectedId.value) || null)
const selectedChildren = computed(() => selectedCategory.value ? props.categories.filter(category => category.parentCategory?.id === selectedCategory.value?.id) : [])
const purposeLabel = computed(() => props.purpose === 'income' ? '收入' : '支出')
const searchModel = computed({ get: () => search.value, set: handleSearch })

function allIds() { return new Set(props.categories.filter(category => category.purpose === props.purpose).map(category => category.id)) }
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
  for (const category of props.categories.filter(item => item.purpose === props.purpose)) {
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
  const siblings = props.categories.filter(category => category.purpose === props.purpose && parentId(category) === parentId(node.category))
  return { position: Math.max(1, siblings.findIndex(category => category.id === node.category.id) + 1), size: siblings.length }
}

function categoryActions(category: Category): DropdownMenuItem[][] {
  return [
    [{ label: '新建子分类', icon: 'i-lucide-plus', onSelect: () => emit('create', category.id) }],
    [
      { label: '编辑', icon: 'i-lucide-pencil', onSelect: () => emit('edit', category) },
      { label: '删除', icon: 'i-lucide-trash-2', color: 'error', onSelect: () => emit('delete', category) },
    ],
  ]
}

watch(() => props.purpose, () => {
  search.value = ''; previousSearchExpansion.value = null
  const ids = allIds(); expandedIds.value = ids
  const first = tree.value.roots[0]?.category
  selectedId.value = first?.id || ''
  focusedId.value = first?.id || ''
})
watch(() => props.categories, (next, previous) => {
  const ids = new Set(next.map(category => category.id))
  if (!initialized.value) { expandedIds.value = new Set([...expandedIds.value, ...allIds()]); initialized.value = true }
  else expandedIds.value = new Set([...expandedIds.value].filter(id => ids.has(id)))
  const oldIds = new Set((previous || []).map(category => category.id))
  const newCategory = next.find(category => !oldIds.has(category.id) && category.purpose === props.purpose)
  const movedCategory = next.find(category => {
    const old = previous?.find(item => item.id === category.id)
    return old && parentId(old) !== parentId(category) && category.purpose === props.purpose
  })
  const changed = newCategory || movedCategory
  if (changed) {
    const parent = parentId(changed)
    if (parent) expandedIds.value = new Set([...expandedIds.value, parent])
    selectedId.value = changed.id; focusedId.value = changed.id
    nextTick(() => document.querySelector<HTMLElement>(`[data-category-id="${CSS.escape(changed.id)}"]`)?.focus())
  } else if (!selectedCategory.value || selectedCategory.value.purpose !== props.purpose) {
    const first = tree.value.roots[0]?.category
    selectedId.value = first?.id || ''
    focusedId.value = first?.id || ''
  }
}, { deep: true, immediate: true })
watch(search, value => { if (value) expandedIds.value = new Set([...expandedIds.value, ...filteredAncestorIds()]) })
</script>

<template>
  <section class="category-workspace" aria-label="分类管理">
    <div class="category-tree-layout">
      <UCard class="category-tree-panel" variant="outline" :ui="{ body: 'p-0 sm:p-0' }">
        <template #header>
          <div>
            <h2 class="font-semibold">{{ purposeLabel }}分类结构</h2>
            <p class="mt-1 text-sm text-muted">使用真实父分类关系组织层级；选择名称查看详情。</p>
          </div>
        </template>

        <div class="category-tree-toolbar">
          <UInput v-model="searchModel" class="min-w-48 flex-1" icon="i-lucide-search" aria-label="搜索分类" placeholder="搜索分类……" />
          <UButton color="neutral" variant="ghost" icon="i-lucide-chevrons-down-up" label="全部展开" @click="expandAll" />
          <UButton color="neutral" variant="ghost" icon="i-lucide-chevrons-up-down" label="全部折叠" @click="collapseAll" />
        </div>

        <UEmpty
          v-if="!filteredRoots.length && !tree.anomalies.length"
          icon="i-lucide-folders"
          :title="search ? '没有匹配的分类' : `暂无${purposeLabel}分类`"
          :description="search ? '请尝试其他名称或清除搜索。' : '使用页面右上角的新建分类按钮开始。'"
          variant="naked"
        />
        <div v-else class="category-tree" role="tree" :aria-label="`${purposeLabel}分类树`">
          <div v-for="node in visibleNodes" :key="node.category.id" :data-category-row-id="node.category.id" class="category-tree-row" :class="{ selected: selectedId === node.category.id }" :style="{ '--depth': node.depth }">
            <div :data-category-id="node.category.id" class="category-tree-item" role="treeitem" :tabindex="focusedId === node.category.id ? 0 : -1" :aria-level="node.depth + 1" :aria-setsize="siblingPosition(node).size" :aria-posinset="siblingPosition(node).position" :aria-expanded="node.children.length ? expandedIds.has(node.category.id) : undefined" :aria-label="`${node.category.name}，${purposeLabel}分类${node.children.length ? `，${node.children.length} 个子分类` : ''}`" @click="selectCategory(node.category)" @keydown="handleKeydown($event, node)">
              <UButton class="tree-toggle" color="neutral" variant="ghost" size="xs" square :icon="node.children.length ? (expandedIds.has(node.category.id) ? 'i-lucide-chevron-down' : 'i-lucide-chevron-right') : 'i-lucide-minus'" :aria-label="node.children.length ? `${expandedIds.has(node.category.id) ? '折叠' : '展开'}${node.category.name}` : `${node.category.name}没有子分类`" :disabled="!node.children.length" @click.stop="node.children.length && toggle(node.category)" />
              <span class="tree-branch" aria-hidden="true">{{ node.depth ? '└─' : '' }}</span><span class="category-icon" :style="{ color: node.category.iconColor, backgroundColor: `${node.category.iconColor}22` }"><UIcon :name="node.category.iconName || 'i-lucide-folder'" /></span>
              <span class="category-tree-name"><strong>{{ node.category.name }}</strong><small>{{ purposeLabel }}<template v-if="node.children.length"> · {{ node.children.length }} 个子分类</template><template v-if="node.category.parentCategory"> · 上级：{{ node.category.parentCategory.name }}</template></small></span>
            </div>
            <UDropdownMenu :items="categoryActions(node.category)" :content="{ align: 'end' }">
              <UButton color="neutral" variant="ghost" size="sm" icon="i-lucide-ellipsis" square :aria-label="`更多操作：${node.category.name}`" @click.stop />
            </UDropdownMenu>
          </div>
        </div>
        <section v-if="tree.anomalies.length" class="category-anomalies" aria-label="需要修复的分类">
          <UAlert color="warning" variant="soft" icon="i-lucide-triangle-alert" title="有分类存在层级异常" description="异常节点仍保留在这里，修复父分类后会回到正常树中。" />
          <div v-for="item in tree.anomalies" :key="item.category.id" class="anomaly-row"><span><strong>{{ item.category.name }}</strong><small>{{ item.reason }}<template v-if="item.category.parentCategory"> · 父级：{{ item.category.parentCategory.name }}</template></small></span><UButton color="neutral" variant="ghost" icon="i-lucide-pencil" label="编辑" :aria-label="`编辑${item.category.name}`" @click="emit('edit', item.category)" /></div>
        </section>
      </UCard>

      <UCard class="category-inspector" variant="outline" aria-label="分类详情">
        <template v-if="selectedCategory" #header>
          <div class="flex min-w-0 items-start justify-between gap-4">
            <div class="min-w-0"><p class="eyebrow">{{ purposeLabel }}分类</p><h2 class="font-semibold">分类详情</h2><p class="category-inspector-title break-words">当前分类：{{ selectedCategory.name }}</p></div>
            <span class="category-inspector-icon" :style="{ color: selectedCategory.iconColor, backgroundColor: `${selectedCategory.iconColor}22` }"><UIcon :name="selectedCategory.iconName || 'i-lucide-folder'" /></span>
          </div>
        </template>
        <template v-if="selectedCategory">
          <dl class="category-detail"><dt>用途</dt><dd>用途：{{ purposeLabel }}</dd><dt>路径</dt><dd>路径：{{ selectedNode?.path || selectedCategory.name }}</dd><dt>父分类</dt><dd>父分类：{{ selectedCategory.parentCategory?.name || '顶级分类' }}</dd><dt>子分类</dt><dd>子分类：{{ selectedChildren.length }} 个</dd><dt>说明</dt><dd>说明：{{ selectedCategory.description || '无' }}</dd></dl>
          <div class="flex flex-wrap gap-2"><UButton label="编辑分类" color="neutral" variant="outline" icon="i-lucide-pencil" @click="emit('edit', selectedCategory)" /><UButton label="新建子分类" icon="i-lucide-plus" @click="emit('create', selectedCategory.id)" /><UButton label="删除" color="error" icon="i-lucide-trash-2" @click="emit('delete', selectedCategory)" /></div>
        </template>
        <UEmpty v-else icon="i-lucide-mouse-pointer-2" title="尚未选择分类" description="从分类树中选择一项查看详情。" variant="naked" />
      </UCard>
    </div>
  </section>
</template>
