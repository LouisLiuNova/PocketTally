<script setup lang="ts">
import type { Category } from '~/types/ledger'
import { buildCategoryTree, findCategoryTrail, type CategoryTreeNode } from '~/utils/categoryTree'
import { DEFAULT_CATEGORY_ICON } from '~/constants/categoryIcons'

const props = defineProps<{ categories: Category[]; purpose: Category['purpose']; modelValue: string; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const tree = computed(() => buildCategoryTree(props.categories, props.purpose))
const pathIds = ref<string[]>([])
const path = computed(() => {
  const nodes: CategoryTreeNode[] = []
  let candidates = tree.value.roots
  for (const id of pathIds.value) {
    const node = candidates.find(item => item.category.id === id)
    if (!node) break
    nodes.push(node)
    candidates = node.children
  }
  return nodes
})
const panel = computed(() => path.value.at(-1) || null)
const selectedTrail = computed(() => findCategoryTrail(tree.value.roots, props.modelValue))
const modalOpen = ref(false)
const picker = ref<HTMLElement | null>(null)
const modalBody = ref<HTMLElement | null>(null)
let trigger: HTMLElement | null = null
const breadcrumbs = computed(() => path.value.map((node, index) => ({ label: node.category.name, depth: index + 1 })))
function selectedDescendant(node: CategoryTreeNode) {
  const index = selectedTrail.value.findIndex(item => item.category.id === node.category.id)
  return index >= 0 && index < selectedTrail.value.length - 1 ? selectedTrail.value.slice(index + 1).map(item => item.category.name).join(' / ') : ''
}
function focusTile(id?: string) {
  const tiles = [...(modalBody.value?.querySelectorAll<HTMLElement>('[data-category-id]') || [])]
  const current = modalBody.value?.querySelector<HTMLElement>('[data-category-current]')
  const target = tiles.find(tile => tile.dataset.categoryId === (id || props.modelValue))
    || (!id && panel.value?.category.id === props.modelValue ? current : null) || tiles[0] || current
  target?.focus()
}
function open(node: CategoryTreeNode, event: MouseEvent) {
  if (props.disabled) return
  if (!node.children.length) { emit('update:modelValue', node.category.id); return }
  trigger = event.currentTarget as HTMLElement
  const selected = selectedTrail.value
  pathIds.value = selected[0]?.category.id === node.category.id ? selected.slice(0, Math.max(1, selected.length - 1)).map(item => item.category.id) : [node.category.id]
  modalOpen.value = true
}
function choose(node: CategoryTreeNode) {
  if (props.disabled) return
  if (!node.children.length) { emit('update:modelValue', node.category.id); return }
  pathIds.value = [...path.value.map(item => item.category.id), node.category.id]
  void nextTick(() => focusTile())
}
function navigate(depth: number) {
  if (props.disabled || depth >= path.value.length) return
  const branchId = path.value[depth]?.category.id
  pathIds.value = path.value.slice(0, depth).map(item => item.category.id)
  void nextTick(() => focusTile(branchId))
}
function chooseCurrent() {
  if (!props.disabled && panel.value) emit('update:modelValue', panel.value.category.id)
}
function restoreFocus(event: Event) {
  event.preventDefault()
  if (trigger?.isConnected) trigger.focus({ preventScroll: true })
  else picker.value?.querySelector<HTMLElement>('[data-category-tile]')?.focus({ preventScroll: true })
}
function onEscape(event: KeyboardEvent) {
  event.stopPropagation()
  event.preventDefault()
  if (props.disabled) return
  if (path.value.length > 1) navigate(path.value.length - 1)
  else modalOpen.value = false
}
watch(() => props.purpose, () => {
  modalOpen.value = false
  pathIds.value = []
})
watch(tree, () => {
  pathIds.value = path.value.map(node => node.category.id)
  if (!panel.value) modalOpen.value = false
  else if (modalOpen.value) void nextTick(() => { if (!modalBody.value?.contains(document.activeElement)) focusTile() })
})
</script>

<template>
  <div ref="picker" class="transaction-category-picker">
    <div v-if="tree.roots.length" class="transaction-category-grid" aria-label="分类">
      <UButton
        v-for="node in tree.roots" :key="node.category.id" data-category-tile :data-category-id="node.category.id"
        type="button" color="neutral" variant="outline" class="transaction-category-tile"
        :ui="{ base: 'rounded-[var(--ui-radius)]' }"
        :class="{ 'transaction-category-tile--selected': modelValue === node.category.id }"
        :aria-label="`${node.category.name}${node.children.length ? '，查看子分类' : '，选择分类'}`"
        :aria-pressed="modelValue === node.category.id" :aria-description="selectedDescendant(node) ? `已选：${selectedDescendant(node)}` : undefined" :disabled="disabled"
        @click="open(node, $event)"
      >
        <span class="transaction-category-icon" :style="{ color: node.category.iconColor, backgroundColor: `${node.category.iconColor}22` }"><UIcon :name="node.category.iconName || DEFAULT_CATEGORY_ICON" aria-hidden="true" /></span>
        <span class="transaction-category-copy"><span class="transaction-category-name">{{ node.category.name }}</span><span v-if="selectedDescendant(node)" class="transaction-category-count">已选：{{ selectedDescendant(node) }}</span><span v-else-if="node.children.length" class="transaction-category-count">{{ node.children.length }} 个子分类</span></span>
        <UIcon v-if="node.children.length" class="transaction-category-state" name="i-lucide-chevron-right" aria-hidden="true" />
        <UIcon v-else-if="modelValue === node.category.id" class="transaction-category-state" name="i-lucide-check" aria-hidden="true" />
      </UButton>
    </div>
    <p v-else class="hint">没有可选分类，请先在「分类与标签」中创建分类。</p>
    <UAlert v-if="tree.anomalies.length" color="warning" variant="soft" icon="i-lucide-triangle-alert" :title="`${tree.anomalies.length} 个异常分类不可选择`" :description="tree.anomalies.map(item => `${item.category.name}：${item.reason}`).join('；')" />
    <UModal :open="modalOpen" :title="panel?.category.name || '选择分类'" :dismissible="!disabled" :close="{ disabled, 'aria-label': '关闭分类选择' }"
      :ui="{ content: 'w-[calc(100vw-2rem)] max-w-xl max-h-[calc(100dvh-2rem)] motion-reduce:animate-none motion-reduce:transition-none', header: 'shrink-0', body: 'min-h-0 overflow-y-auto' }"
      :content="{ onEscapeKeyDown: onEscape, onCloseAutoFocus: restoreFocus }"
      @update:open="value => { if (!disabled) modalOpen = value }" @after:enter="focusTile()">
      <template #body>
        <div v-if="panel" ref="modalBody" class="transaction-category-panel">
          <div class="transaction-category-panel-heading">
            <UButton v-if="path.length > 1" type="button" color="neutral" variant="ghost" icon="i-lucide-arrow-left" label="返回上级" :disabled="disabled" @click="navigate(path.length - 1)" />
            <UBreadcrumb v-if="path.length > 1" :items="breadcrumbs" aria-label="分类层级" :ui="{ list: 'flex-wrap gap-y-1' }">
              <template #item="{ item }">
                <UButton v-if="item.depth < path.length" type="button" color="neutral" variant="link" :label="item.label" :disabled="disabled" class="min-h-11 p-1" @click="navigate(item.depth)" />
                <span v-else class="font-medium text-default break-all" aria-current="page">{{ item.label }}</span>
              </template>
            </UBreadcrumb>
          </div>
          <p v-if="selectedTrail.length" role="status" class="text-sm text-primary break-words">已选择：{{ selectedTrail.map(node => node.category.name).join(' / ') }}</p>
          <UButton data-category-current type="button" class="whitespace-normal text-left break-words" color="neutral" variant="outline" :icon="modelValue === panel.category.id ? 'i-lucide-check' : undefined" :class="{ 'transaction-category-tile--selected': modelValue === panel.category.id }" :label="`选择当前分类：${panel.category.name}`" :aria-pressed="modelValue === panel.category.id" :disabled="disabled" @click="chooseCurrent" />
          <div v-if="panel.children.length" class="transaction-category-grid" aria-label="子分类">
            <UButton
              v-for="node in panel.children" :key="node.category.id" data-category-tile :data-category-id="node.category.id"
              type="button" color="neutral" variant="outline" class="transaction-category-tile"
              :ui="{ base: 'rounded-[var(--ui-radius)]' }"
              :class="{ 'transaction-category-tile--selected': modelValue === node.category.id }"
              :aria-label="`${node.category.name}${node.children.length ? '，查看子分类' : '，选择分类'}`"
              :aria-pressed="modelValue === node.category.id" :aria-description="selectedDescendant(node) ? `已选：${selectedDescendant(node)}` : undefined" :disabled="disabled"
              @click="choose(node)"
            >
              <span class="transaction-category-icon" :style="{ color: node.category.iconColor, backgroundColor: `${node.category.iconColor}22` }"><UIcon :name="node.category.iconName || DEFAULT_CATEGORY_ICON" aria-hidden="true" /></span>
              <span class="transaction-category-copy"><span class="transaction-category-name">{{ node.category.name }}</span><span v-if="selectedDescendant(node)" class="transaction-category-count">已选：{{ selectedDescendant(node) }}</span><span v-else-if="node.children.length" class="transaction-category-count">{{ node.children.length }} 个子分类</span></span>
              <UIcon v-if="node.children.length" class="transaction-category-state" name="i-lucide-chevron-right" aria-hidden="true" />
              <UIcon v-else-if="modelValue === node.category.id" class="transaction-category-state" name="i-lucide-check" aria-hidden="true" />
            </UButton>
          </div>
          <p v-else class="hint">当前分类没有子分类，可选择当前分类。</p>
        </div>
      </template>
    </UModal>
  </div>
</template>

<style scoped>
.transaction-category-picker { display: grid; gap: 10px; min-width: 0; }
.transaction-category-panel { display: grid; gap: 12px; min-width: 0; }
.transaction-category-panel-heading { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; min-width: 0; }
.transaction-category-panel-heading nav { min-width: 0; }
.transaction-category-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; }
.transaction-category-tile { position: relative; min-width: 0; min-height: 48px; display: flex; align-items: center; justify-content: flex-start; gap: 8px; padding: 8px 24px 8px 10px; white-space: normal; }
.transaction-category-tile--selected { outline: 2px solid var(--ui-primary); outline-offset: -2px; background: var(--pt-primary-container); }
.transaction-category-state { position: absolute; top: 50%; right: 7px; transform: translateY(-50%); width: 14px; height: 14px; color: var(--ui-text-muted); }
.transaction-category-tile--selected .transaction-category-state { color: var(--ui-primary); }
.transaction-category-icon { display: grid; place-items: center; flex-shrink: 0; width: 28px; height: 28px; border-radius: 6px; }
.transaction-category-icon :deep(.iconify) { width: 18px; height: 18px; }
.transaction-category-name { min-width: 0; text-align: left; overflow-wrap: anywhere; font-size: .875rem; line-height: 1.4; }
.transaction-category-copy { display: grid; gap: 2px; min-width: 0; text-align: left; }
.transaction-category-count { color: var(--ui-text-muted); font-size: .75rem; line-height: 1.3; }
@media (max-width: 560px) {
  .transaction-category-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
