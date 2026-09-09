<script setup lang="ts">
import type { Account, Category, Tag } from '~/types/ledger'
import { errorMessage } from '~/composables/useLedger'
const props = defineProps<{ kind: 'accounts' | 'categories' | 'tags'; item?: Account | Category | Tag; categories: Category[]; initialParentCategoryId?: string }>()
const emit = defineEmits<{ close: []; saved: [] }>()
const names = { accounts: '账户', categories: '分类', tags: '标签' }
const item = props.item
const form = reactive({ name: item?.name || '', description: item?.description || '', type: (item as Account)?.type || 'debit', purpose: (item as Category)?.purpose || 'expense', parentCategoryId: (item as Category)?.parentCategory?.id || props.initialParentCategoryId || '', color: (item as Tag)?.color || (item as Category)?.iconColor || '#005CAF', cardNumber: (item as Account)?.cardNumber || '' })
const busy = ref(false)
const error = ref('')
const moveConfirmed = ref(false)
const moving = computed(() => props.kind === 'categories' && !!item && form.parentCategoryId !== ((item as Category).parentCategory?.id || ''))
const parents = computed(() => props.categories.filter(c => {
  if (c.purpose !== form.purpose) return false
  const seen = new Set<string>()
  let current: Category | undefined = c
  while (current) {
    if (current.id === item?.id || seen.has(current.id)) return false
    seen.add(current.id)
    current = props.categories.find(p => p.id === current!.parentCategory?.id)
  }
  return true
}))
const selectedParent = computed(() => props.categories.find(category => category.id === form.parentCategoryId))
const selectedParentPath = computed(() => {
  if (!selectedParent.value) return '顶级分类'
  const names = [selectedParent.value.name]; const seen = new Set([selectedParent.value.id]); let current = selectedParent.value
  while (current.parentCategory && !seen.has(current.parentCategory.id)) {
    const parent = props.categories.find(category => category.id === current.parentCategory?.id)
    if (!parent) break
    names.unshift(parent.name); seen.add(parent.id); current = parent
  }
  return `${form.purpose === 'income' ? '收入' : '支出'} / ${names.join(' / ')}`
})
watch(() => form.purpose, () => { form.parentCategoryId = '' })
watch(() => form.parentCategoryId, () => { moveConfirmed.value = false })
async function save() {
  if (busy.value) return
  if (!form.name.trim()) { error.value = '名称不能为空'; return }
  if (moving.value && !moveConfirmed.value) { error.value = '请确认移动分类及其整个子树'; return }
  let body: object = { name: form.name.trim(), description: form.description.trim() || null }
  if (props.kind === 'accounts') body = { ...body, type: form.type, cardNumber: form.cardNumber.trim() || null }
  if (props.kind === 'tags') body = { ...body, color: form.color }
  if (props.kind === 'categories') body = { ...body, ...(!item ? { purpose: form.purpose } : {}), parentCategoryId: form.parentCategoryId || null, iconColor: form.color, iconName: (item as Category)?.iconName || 'i-lucide-folder' }
  busy.value = true; error.value = ''
  try {
    await $fetch(`/api/v1/${props.kind}${item ? `/${item.id}` : ''}`, { method: item ? 'PATCH' : 'POST', body, retry: 0 })
    emit('saved')
  } catch (e) { error.value = errorMessage(e) }
  finally { busy.value = false }
}
</script>
<template>
  <form class="composer" :aria-busy="busy" @submit.prevent="save">
    <header><h2>{{ item ? '编辑' : '新建' }}{{ names[kind] }}</h2><button type="button" aria-label="关闭" :disabled="busy" @click="emit('close')">×</button></header>
    <fieldset :disabled="busy" :aria-disabled="busy">
      <label>名称<input v-model="form.name" required autofocus></label>
      <template v-if="kind === 'accounts'">
        <label>账户类型<select v-model="form.type"><option value="debit">借记账户（余额不可为负）</option><option value="credit">信用账户（允许负余额）</option></select></label>
        <label>卡号 / 尾号<input v-model="form.cardNumber"></label>
        <p class="hint">新账户余额为 0。保存后使用「调账」录入现有余额。</p>
      </template>
      <template v-if="kind === 'categories'">
        <label>用途<select v-model="form.purpose" :disabled="!!item"><option value="expense">支出</option><option value="income">收入</option></select></label>
        <label>父分类<select v-model="form.parentCategoryId"><option value="">顶级分类</option><option v-for="c in parents" :key="c.id" :value="c.id">{{ c.name }}</option></select></label>
        <p class="hint parent-path">父分类路径：{{ selectedParentPath }}</p>
        <label v-if="moving" class="check-label"><input v-model="moveConfirmed" type="checkbox">确认将此分类及其所有子分类一起移动</label>
      </template>
      <label v-if="kind !== 'accounts'">颜色<input v-model="form.color" type="color"></label>
      <label>说明<input v-model="form.description"></label>
    </fieldset>
    <p v-if="error" role="alert" aria-live="assertive" class="error-box">{{ error }}</p>
    <div class="composer-actions"><span>名称不能重复</span><UButton type="submit" label="保存" :loading="busy" :aria-busy="busy" :disabled="busy" /></div>
  </form>
</template>
