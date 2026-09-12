<script setup lang="ts">
import type { Category } from '~/types/ledger'

const workspace = useLedgerWorkspace()
type ResourceTab = Category['purpose'] | 'tags'
const activeTab = ref<ResourceTab>('expense')
const activePurpose = computed<Category['purpose']>(() => activeTab.value === 'income' ? 'income' : 'expense')
const tabItems = computed(() => [
  { label: '支出分类', value: 'expense', icon: 'i-lucide-circle-minus', badge: workspace.categories.value.filter(category => category.purpose === 'expense').length },
  { label: '收入分类', value: 'income', icon: 'i-lucide-circle-plus', badge: workspace.categories.value.filter(category => category.purpose === 'income').length },
  { label: '标签', value: 'tags', icon: 'i-lucide-tags', badge: workspace.tags.value.length },
])

function createActiveResource() {
  if (activeTab.value === 'tags') workspace.resourceEditor.value = { kind: 'tags' }
  else workspace.createCategory(undefined, activePurpose.value)
}

function handleTabBoundaryKeydown(event: KeyboardEvent) {
  if (event.key !== 'Home' && event.key !== 'End') return
  event.preventDefault()
  event.stopPropagation()
  const nextValue: ResourceTab = event.key === 'Home' ? 'expense' : 'tags'
  activeTab.value = nextValue
  const root = event.currentTarget as HTMLElement
  nextTick(() => window.setTimeout(() => root.querySelectorAll<HTMLElement>('[role="tab"]')[event.key === 'Home' ? 0 : 2]?.focus(), 0))
}
</script>

<template>
  <section class="page-flow resource-management-page">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div @keydown.capture="handleTabBoundaryKeydown">
        <UTabs v-model="activeTab" :items="tabItems" :content="false" variant="link" aria-label="资源类型" />
      </div>
      <UButton
        icon="i-lucide-plus"
        :label="activeTab === 'tags' ? '新建标签' : '新建分类'"
        @click="createActiveResource"
      />
    </div>

    <CategoryTree
      v-if="activeTab !== 'tags'"
      :categories="workspace.categories.value"
      :purpose="activePurpose"
      @create="parentCategoryId => workspace.createCategory(parentCategoryId, activePurpose)"
      @edit="category => workspace.resourceEditor.value = { kind: 'categories', item: category }"
      @delete="category => workspace.deleteResource('categories', category)"
    />

    <UCard v-else variant="outline" :ui="{ body: 'p-0 sm:p-0' }">
      <template #header>
        <div>
          <h2 class="font-semibold">标签</h2>
          <p class="mt-1 text-sm text-muted">使用标签标记项目、旅行或其他跨分类用途。</p>
        </div>
      </template>

      <UEmpty
        v-if="workspace.loaded.value && !workspace.tags.value.length"
        icon="i-lucide-tags"
        title="暂无标签"
        description="标签是可选资源，可以在记账时为交易补充上下文。"
      />

      <div v-else class="divide-y divide-default">
        <div v-for="tag in workspace.tags.value" :key="tag.id" :data-tag-id="tag.id" class="flex min-w-0 items-center gap-3 px-4 py-4 sm:px-6">
          <span class="tag-color-dot size-3 shrink-0 rounded-full ring-1 ring-default" :style="{ backgroundColor: tag.color }" aria-hidden="true" />
          <div class="min-w-0 flex-1">
            <strong class="block break-words text-sm">{{ tag.name }}</strong>
            <p class="mt-1 break-words text-xs text-muted">{{ tag.description || '无说明' }}</p>
          </div>
          <div class="flex shrink-0 items-center gap-1">
            <UButton color="neutral" variant="ghost" icon="i-lucide-pencil" label="编辑" @click="workspace.resourceEditor.value = { kind: 'tags', item: tag }" />
            <UButton color="error" variant="ghost" icon="i-lucide-trash-2" label="删除" @click="workspace.deleteResource('tags', tag)" />
          </div>
        </div>
      </div>
    </UCard>
  </section>
</template>
