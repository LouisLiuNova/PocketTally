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
const selected = computed(() => props.categories.find(category => category.id === props.modelValue))
const picker = ref<HTMLElement | null>(null)

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
    <p v-if="selected" class="transaction-category-selection"><UIcon name="i-lucide-circle-check" aria-hidden="true" />已选择：{{ selected.name }}</p>
    <div v-if="panel" class="transaction-category-panel" role="group" :aria-label="`${panel.category.name}的子分类`">
      <div class="transaction-category-panel-heading">
        <UButton data-category-back type="button" color="neutral" variant="ghost" icon="i-lucide-arrow-left" label="返回上级" :disabled="disabled" @click="back" />
        <span>{{ panel.path }}</span>
        <UButton type="button" color="neutral" variant="ghost" label="取消" :disabled="disabled" @click="cancelPanel" />
      </div>
      <UButton type="button" class="w-full" color="primary" variant="soft" icon="i-lucide-check" :label="`选择当前分类：${panel.category.name}`" :disabled="disabled" @click="chooseCurrent" />
    </div>
    <div v-if="visible.length" class="transaction-category-grid" :aria-label="panel ? '子分类' : '分类'">
      <UButton
        v-for="node in visible" :key="node.category.id" data-category-tile
        type="button" color="neutral" variant="outline" class="transaction-category-tile"
        :class="{ 'transaction-category-tile--selected': modelValue === node.category.id }"
        :aria-label="`${node.category.name}${node.children.length ? '，查看子分类' : '，选择分类'}`"
        :aria-pressed="modelValue === node.category.id" :disabled="disabled"
        @click="open(node)"
      >
        <span class="transaction-category-icon" :style="{ color: node.category.iconColor, backgroundColor: `${node.category.iconColor}22` }"><UIcon :name="node.category.iconName || DEFAULT_CATEGORY_ICON" aria-hidden="true" /></span>
        <span class="transaction-category-name">{{ node.category.name }}</span>
        <UIcon v-if="node.children.length" name="i-lucide-chevron-right" aria-hidden="true" />
        <UIcon v-else-if="modelValue === node.category.id" name="i-lucide-check" aria-hidden="true" />
      </UButton>
    </div>
    <p v-else class="hint">{{ panel ? '当前分类没有子分类，可选择当前分类。' : '没有可选分类，请先在「分类与标签」中创建分类。' }}</p>
    <UAlert v-if="tree.anomalies.length" color="warning" variant="soft" icon="i-lucide-triangle-alert" :title="`${tree.anomalies.length} 个异常分类不可选择`" :description="tree.anomalies.map(item => `${item.category.name}：${item.reason}`).join('；')" />
  </div>
</template>

<style scoped>
.transaction-category-picker { display: grid; gap: 10px; min-width: 0; }
.transaction-category-selection { display: flex; align-items: center; gap: 6px; color: var(--ui-primary); font-size: .875rem; }
.transaction-category-panel { display: grid; gap: 8px; padding: 10px; border: 1px solid var(--ui-border); border-radius: var(--ui-radius); background: var(--ui-bg-elevated); }
.transaction-category-panel-heading { display: flex; align-items: center; gap: 8px; min-width: 0; }
.transaction-category-panel-heading span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: .875rem; }
.transaction-category-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(105px, 1fr)); gap: 8px; }
.transaction-category-tile { min-width: 0; min-height: 74px; display: flex; flex-direction: column; gap: 3px; padding: 8px; white-space: normal; }
.transaction-category-tile--selected { outline: 2px solid var(--ui-primary); outline-offset: -2px; }
.transaction-category-icon { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 8px; }
.transaction-category-name { max-width: 100%; overflow-wrap: anywhere; font-size: .8rem; line-height: 1.2; }
</style>
