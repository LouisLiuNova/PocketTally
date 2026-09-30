<script setup lang="ts">
import type { Category } from '~/types/ledger'
import { buildCategoryTree, type CategoryTreeNode } from '~/utils/categoryTree'
import { DEFAULT_CATEGORY_ICON } from '~/constants/categoryIcons'

const props = defineProps<{ categories: Category[]; purpose: Category['purpose']; modelValue: string; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const tree = computed(() => buildCategoryTree(props.categories, props.purpose))
const path = ref<CategoryTreeNode[]>([])
const panel = computed(() => path.value.at(-1) || null)
const visible = computed(() => panel.value?.children || tree.value.roots)
const picker = ref<HTMLElement | null>(null)
const breadcrumbs = computed(() => [{ label: '全部分类', depth: 0 }, ...path.value.map((node, index) => ({ label: node.category.name, depth: index + 1 }))])

function navigate(depth: number) {
  if (props.disabled) return
  path.value = path.value.slice(0, depth)
  void nextTick(() => picker.value?.querySelector<HTMLElement>(panel.value ? '[data-category-back]' : '[data-category-tile]')?.focus())
}

watch(() => props.purpose, () => { path.value = [] })

function open(node: CategoryTreeNode) {
  if (props.disabled) return
  if (!node.children.length) { emit('update:modelValue', node.category.id); path.value = []; return }
  path.value = [...path.value, node]
  void nextTick(() => picker.value?.querySelector<HTMLElement>('[data-category-back]')?.focus())
}

function back() {
  path.value = path.value.slice(0, -1)
  void nextTick(() => picker.value?.querySelector<HTMLElement>(panel.value ? '[data-category-back]' : '[data-category-tile]')?.focus())
}

function chooseCurrent() {
  if (!panel.value) return
  emit('update:modelValue', panel.value.category.id)
  path.value = []
  void nextTick(() => picker.value?.querySelector<HTMLElement>('[data-category-tile]')?.focus())
}

function cancelPanel() {
  path.value = []
  void nextTick(() => picker.value?.querySelector<HTMLElement>('[data-category-tile]')?.focus())
}

function onEscape(event: KeyboardEvent) {
  if (!panel.value) return
  event.stopPropagation()
  event.preventDefault()
  back()
}
</script>

<template>
  <div ref="picker" class="transaction-category-picker" @keydown.esc="onEscape">
    <div v-if="panel" class="transaction-category-panel" role="group" :aria-label="`${panel.category.name}的子分类`">
      <div class="transaction-category-panel-heading">
        <UButton data-category-back type="button" color="neutral" variant="ghost" icon="i-lucide-arrow-left" label="返回上级" :disabled="disabled" @click="back" />
        <UButton type="button" color="neutral" variant="ghost" label="取消" :disabled="disabled" @click="cancelPanel" />
      </div>
      <UBreadcrumb :items="breadcrumbs" aria-label="分类层级" :ui="{ list: 'flex-wrap gap-y-1' }">
        <template #item="{ item }">
          <UButton v-if="item.depth < path.length" type="button" color="neutral" variant="link" :label="item.label" :disabled="disabled" class="min-h-11 p-1" @click="navigate(item.depth)" />
          <span v-else class="font-medium text-default" aria-current="page">{{ item.label }}</span>
        </template>
      </UBreadcrumb>
      <UButton type="button" class="w-full" color="primary" variant="soft" icon="i-lucide-check" :label="`选择当前分类：${panel.category.name}`" :disabled="disabled" @click="chooseCurrent" />
    </div>
    <div v-if="visible.length" class="transaction-category-grid" :aria-label="panel ? '子分类' : '分类'">
      <UButton
        v-for="node in visible" :key="node.category.id" data-category-tile
        type="button" color="neutral" variant="outline" class="transaction-category-tile"
        :ui="{ base: 'rounded-[var(--ui-radius)]' }"
        :class="{ 'transaction-category-tile--selected': modelValue === node.category.id }"
        :aria-label="`${node.category.name}${node.children.length ? '，查看子分类' : '，选择分类'}`"
        :aria-pressed="modelValue === node.category.id" :disabled="disabled"
        @click="open(node)"
      >
        <span class="transaction-category-icon" :style="{ color: node.category.iconColor, backgroundColor: `${node.category.iconColor}22` }"><UIcon :name="node.category.iconName || DEFAULT_CATEGORY_ICON" aria-hidden="true" /></span>
        <span class="transaction-category-copy"><span class="transaction-category-name">{{ node.category.name }}</span><span v-if="node.children.length" class="transaction-category-count">{{ node.children.length }} 个子分类</span></span>
        <UIcon v-if="node.children.length" class="transaction-category-state" name="i-lucide-chevron-right" aria-hidden="true" />
        <UIcon v-else-if="modelValue === node.category.id" class="transaction-category-state" name="i-lucide-check" aria-hidden="true" />
      </UButton>
    </div>
    <p v-else class="hint">{{ panel ? '当前分类没有子分类，可选择当前分类。' : '没有可选分类，请先在「分类与标签」中创建分类。' }}</p>
    <UAlert v-if="tree.anomalies.length" color="warning" variant="soft" icon="i-lucide-triangle-alert" :title="`${tree.anomalies.length} 个异常分类不可选择`" :description="tree.anomalies.map(item => `${item.category.name}：${item.reason}`).join('；')" />
  </div>
</template>

<style scoped>
.transaction-category-picker { display: grid; gap: 10px; min-width: 0; }
.transaction-category-panel { display: grid; gap: 8px; padding: 10px; border: 1px solid var(--ui-border); border-radius: var(--ui-radius); background: var(--ui-bg-elevated); }
.transaction-category-panel-heading { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-width: 0; }
.transaction-category-panel-heading span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: .875rem; }
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
