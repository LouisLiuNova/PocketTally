<script setup lang="ts">
import type { Account, Category, Tag } from '~/types/ledger'
import { errorMessage } from '~/composables/useLedger'
import { colorValidationMessage, isValidHexColor } from '~/utils/color'

const props = defineProps<{ kind: 'accounts' | 'categories' | 'tags'; item?: Account | Category | Tag; categories: Category[]; initialParentCategoryId?: string; initialPurpose?: Category['purpose'] }>()
const emit = defineEmits<{ close: []; saved: []; busy: [value: boolean] }>()
const names = { accounts: '账户', categories: '分类', tags: '标签' }
const item = props.item
const form = reactive({ name: item?.name || '', description: item?.description || '', type: (item as Account)?.type || 'debit', purpose: (item as Category)?.purpose || props.initialPurpose || 'expense', parentCategoryId: (item as Category)?.parentCategory?.id || props.initialParentCategoryId || '', color: (item as Tag)?.color || (item as Category)?.iconColor || '#005CAF', cardNumber: (item as Account)?.cardNumber || '' })
const busy = ref(false)
const error = ref('')
const moveConfirmed = ref(false)
const colorError = computed(() => props.kind !== 'accounts' && !isValidHexColor(form.color) ? colorValidationMessage(form.color) : '')
const moving = computed(() => props.kind === 'categories' && !!item && form.parentCategoryId !== ((item as Category).parentCategory?.id || ''))
const editorTitle = computed(() => {
  const resourceName = props.kind === 'categories' && !item
    ? `${form.purpose === 'income' ? '收入' : '支出'}分类`
    : names[props.kind]
  return `${item ? '编辑' : '新建'}${resourceName}`
})
const accountTypeItems = [
  { label: '借记账户（余额不可为负）', value: 'debit' },
  { label: '信用账户（允许负余额）', value: 'credit' },
]
const categoryPurposeItems = [
  { label: '支出', value: 'expense' },
  { label: '收入', value: 'income' },
]
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
const parentItems = computed(() => [
  { label: '顶级分类', value: '' },
  ...parents.value.map(category => ({ label: category.name, value: category.id })),
])
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
  if (colorError.value) { error.value = ''; return }
  if (moving.value && !moveConfirmed.value) { error.value = '请确认移动分类及其整个子树'; return }
  let body: object = { name: form.name.trim(), description: form.description.trim() || null }
  if (props.kind === 'accounts') body = { ...body, type: form.type, cardNumber: form.cardNumber.trim() || null }
  if (props.kind === 'tags') body = { ...body, color: form.color }
  if (props.kind === 'categories') body = { ...body, ...(!item ? { purpose: form.purpose } : {}), parentCategoryId: form.parentCategoryId || null, iconColor: form.color, iconName: (item as Category)?.iconName || 'i-lucide-folder' }
  busy.value = true; error.value = ''; emit('busy', true)
  try {
    await $fetch(`/api/v1/${props.kind}${item ? `/${item.id}` : ''}`, { method: item ? 'PATCH' : 'POST', body, retry: 0 })
    emit('saved')
  } catch (e) { error.value = errorMessage(e) }
  finally { busy.value = false; emit('busy', false) }
}
</script>

<template>
  <UForm :state="form" class="w-full space-y-4 p-4 pb-5 sm:p-6 sm:pb-7" :disabled="busy" :aria-busy="busy" @submit="save">
    <header class="flex items-start justify-between gap-4"><h2>{{ editorTitle }}</h2><UButton color="neutral" variant="ghost" icon="i-lucide-x" aria-label="关闭" :disabled="busy" @click="emit('close')" /></header>
    <UFormField name="name" label="名称" required>
      <UInput id="resource-name" v-model="form.name" autofocus class="w-full" />
    </UFormField>
    <template v-if="kind === 'accounts'">
      <UFormField name="type" label="账户类型" required>
        <USelect v-model="form.type" :items="accountTypeItems" class="w-full" />
      </UFormField>
      <UFormField name="cardNumber" label="卡号 / 尾号">
        <UInput v-model="form.cardNumber" class="w-full" />
      </UFormField>
      <p class="hint">新账户余额为 0。保存后使用「调账」录入现有余额。</p>
    </template>
    <template v-if="kind === 'categories'">
      <UFormField name="purpose" label="用途" required>
        <USelect v-model="form.purpose" :items="categoryPurposeItems" disabled class="w-full" />
      </UFormField>
      <UFormField name="parentCategoryId" label="父分类">
        <USelect v-model="form.parentCategoryId" :items="parentItems" class="w-full" />
      </UFormField>
      <p class="hint parent-path">父分类路径：{{ selectedParentPath }}</p>
      <UCheckbox v-if="moving" v-model="moveConfirmed" label="确认将此分类及其所有子分类一起移动" />
    </template>
    <UFormField v-if="kind !== 'accounts'" name="color" label="颜色" required :error="colorError || undefined">
      <ColorInput v-model="form.color" id="resource-color" :error="colorError" :disabled="busy" />
    </UFormField>
    <UFormField name="description" label="说明">
      <UTextarea v-model="form.description" :rows="3" class="w-full" />
    </UFormField>
    <UAlert v-if="error" color="error" variant="soft" icon="i-lucide-circle-alert" title="保存失败" :description="error" role="alert" aria-live="assertive" />
    <div class="flex items-center justify-between gap-3 pt-2"><span class="text-sm text-dimmed">名称不能重复</span><UButton type="submit" label="保存" :loading="busy" :aria-busy="busy" :disabled="busy" /></div>
  </UForm>
</template>
