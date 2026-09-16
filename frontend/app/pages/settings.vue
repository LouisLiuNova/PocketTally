<script setup lang="ts">
import { APPEARANCE_PALETTES, type PaletteName, type ThemePreference } from '~/constants/appearance'

const workspace = useLedgerWorkspace()

const themeOptions: Array<{ value: ThemePreference; label: string; description: string; icon: string }> = [
  { value: 'system', label: '跟随系统', description: '根据设备的外观偏好自动切换', icon: 'i-lucide-monitor' },
  { value: 'light', label: '亮色', description: '始终使用明亮背景', icon: 'i-lucide-sun' },
  { value: 'dark', label: '暗色', description: '始终使用深色背景', icon: 'i-lucide-moon' },
]

const selectedPalette = computed(() => APPEARANCE_PALETTES.find(item => item.value === workspace.palette.value))
const paletteOptions = APPEARANCE_PALETTES.map(item => ({
  ...item,
  label: `${item.label} ${item.description}`,
  displayLabel: item.label,
}))
function selectPaletteWithArrow(event: KeyboardEvent) {
  if (!['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp'].includes(event.key)) return
  const target = event.target as HTMLElement
  if (target.getAttribute('role') !== 'radio' || !target.closest('.palette-choice')) return

  event.preventDefault()
  event.stopPropagation()
  const current = target.getAttribute('value') as PaletteName
  const currentIndex = APPEARANCE_PALETTES.findIndex(item => item.value === current)
  const offset = event.key === 'ArrowRight' || event.key === 'ArrowDown' ? 1 : -1
  const nextIndex = (currentIndex + offset + APPEARANCE_PALETTES.length) % APPEARANCE_PALETTES.length
  const nextPalette = APPEARANCE_PALETTES[nextIndex]!.value
  workspace.palette.value = nextPalette
  nextTick(() => document.querySelector<HTMLButtonElement>(`.palette-choice [role="radio"][value="${nextPalette}"]`)?.focus())
}
</script>

<template>
  <section class="page-flow page-flow--settings settings-page">
    <header class="settings-intro">
      <div>
        <p class="eyebrow">偏好设置</p>
        <h2>外观</h2>
        <p class="hint">主题和配色会立即生效。</p>
      </div>
      <span class="settings-intro-icon" aria-hidden="true"><UIcon name="i-lucide-sliders-horizontal" /></span>
    </header>

    <UCard class="settings-card" variant="outline">
      <template #header>
        <div class="settings-card-heading">
          <div>
            <h3>主题模式</h3>
            <p>选择明暗主题，或跟随设备的系统设置。</p>
          </div>
          <UIcon name="i-lucide-sun-moon" aria-hidden="true" />
        </div>
      </template>
      <URadioGroup
        v-model="workspace.theme.value"
        :items="themeOptions"
        variant="card"
        orientation="horizontal"
        color="primary"
        indicator="start"
        legend="主题模式"
        :ui="{ root: 'settings-theme-group', legend: 'sr-only', fieldset: 'settings-theme-options', item: 'settings-theme-option', wrapper: 'settings-theme-copy' }"
      >
        <template #label="{ item }">
          <span class="settings-theme-label">
            <UIcon :name="item.icon" aria-hidden="true" />
            <span>{{ item.label }}</span>
          </span>
        </template>
      </URadioGroup>
    </UCard>

    <UCard class="settings-card" variant="outline">
      <template #header>
        <div class="settings-card-heading">
          <div>
            <h3>配色</h3>
            <p>选择喜欢的配色。</p>
          </div>
          <span class="settings-current-palette">当前：{{ selectedPalette?.label }}</span>
        </div>
      </template>
      <URadioGroup
        v-model="workspace.palette.value"
        :items="paletteOptions"
        value-key="value"
        variant="card"
        orientation="horizontal"
        indicator="hidden"
        color="primary"
        legend="配色预设"
        :ui="{ root: 'palette-picker', legend: 'sr-only', fieldset: 'palette-grid', item: 'palette-choice', wrapper: 'palette-choice-wrapper', label: 'palette-choice-label', description: 'sr-only' }"
        @keydown.capture="selectPaletteWithArrow"
      >
        <template #label="{ item }">
          <span class="palette-preview" :data-palette-preview="item.value" aria-hidden="true">
            <span class="palette-preview-sidebar"><i /></span>
            <span class="palette-preview-main">
              <span class="palette-preview-toolbar"><i /><i /></span>
              <span class="palette-preview-cards"><i /><i /></span>
              <span class="palette-preview-chart"><i /><i /><i /><i /></span>
              <span class="palette-preview-action" />
            </span>
          </span>
          <span class="palette-choice-copy">
            <strong aria-hidden="true">{{ item.displayLabel }}</strong>
            <span class="sr-only">{{ item.description }}</span>
            <UIcon v-if="workspace.palette.value === item.value" name="i-lucide-check" class="palette-choice-check" aria-hidden="true" />
          </span>
        </template>
      </URadioGroup>
      <p class="settings-selection-status" role="status">已选择「{{ selectedPalette?.label }}」配色</p>
    </UCard>

  </section>
</template>
