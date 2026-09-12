<script setup lang="ts">
import { isValidHexColor } from '~/utils/color'

const props = withDefaults(defineProps<{
  modelValue: string
  id?: string
  disabled?: boolean
  error?: string
}>(), {
  id: 'resource-color',
  disabled: false,
  error: '',
})

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const pickerValue = ref(isValidHexColor(props.modelValue) ? props.modelValue : '#005CAF')

watch(() => props.modelValue, value => {
  if (isValidHexColor(value)) pickerValue.value = value
})

const pickerId = computed(() => `${props.id}-picker`)
const errorId = computed(() => `${props.id}-error`)
const previewColor = computed(() => isValidHexColor(props.modelValue) ? props.modelValue : pickerValue.value)

function updateText(value: string) {
  emit('update:modelValue', value)
}

function updatePicker(event: Event) {
  const value = (event.target as HTMLInputElement).value
  pickerValue.value = value
  emit('update:modelValue', value)
}
</script>

<template>
  <div class="color-input-control">
    <span class="color-input-preview" :style="{ backgroundColor: previewColor }" aria-hidden="true" />
    <input
      :id="pickerId"
      class="color-input-picker"
      type="color"
      :value="pickerValue"
      aria-label="颜色选择器"
      :disabled="disabled"
      @input="updatePicker"
    >
    <UInput
      :id="id"
      :model-value="modelValue"
      type="text"
      inputmode="text"
      autocomplete="off"
      spellcheck="false"
      placeholder="#RRGGBB"
      aria-label="颜色值（#RRGGBB）"
      :aria-invalid="!!error"
      :aria-describedby="error ? errorId : undefined"
      :disabled="disabled"
      class="color-input-text"
      @update:model-value="updateText"
    />
    <span class="sr-only" aria-live="polite">{{ isValidHexColor(modelValue) ? `当前颜色 ${modelValue}` : '颜色值无效' }}</span>
    <span v-if="error" :id="errorId" class="color-input-error" role="alert">{{ error }}</span>
  </div>
</template>
