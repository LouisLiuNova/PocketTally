<script setup lang="ts">
const workspace = useLedgerWorkspace()
</script>

<template>
  <section class="page-flow page-grid taxonomy-grid">
    <CategoryTree
      :categories="workspace.categories.value"
      @create="workspace.createCategory"
      @edit="category => workspace.resourceEditor.value = { kind: 'categories', item: category }"
      @delete="category => workspace.deleteResource('categories', category)"
    />
    <article class="panel taxonomy-tags">
      <div class="panel-head"><h2>标签</h2><UButton label="新建标签" @click="workspace.resourceEditor.value = { kind: 'tags' }" /></div>
      <p v-if="!workspace.tags.value.length" class="empty-state">标签可选，用来标记项目、旅行或其他用途。</p>
      <div v-for="tag in workspace.tags.value" :key="tag.id" class="resource-row">
        <span><i class="color-dot" :style="{ background: tag.color }" />{{ tag.name }}</span>
        <div><button class="text-link" @click="workspace.resourceEditor.value = { kind: 'tags', item: tag }">编辑</button><button class="text-link danger" @click="workspace.deleteResource('tags', tag)">删除</button></div>
      </div>
    </article>
  </section>
</template>
