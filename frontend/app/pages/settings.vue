<script setup lang="ts">
import { APPEARANCE_PALETTES, type ThemePreference } from '~/constants/appearance'

const workspace = useLedgerWorkspace()

const themeOptions: Array<{ value: ThemePreference; label: string; description: string; icon: string }> = [
  { value: 'system', label: '跟随系统', description: '根据设备的外观偏好自动切换', icon: 'i-lucide-monitor' },
  { value: 'light', label: '亮色', description: '始终使用明亮背景', icon: 'i-lucide-sun' },
  { value: 'dark', label: '暗色', description: '始终使用深色背景', icon: 'i-lucide-moon' },
]

const selectedPalette = computed(() => APPEARANCE_PALETTES.find(item => item.value === workspace.palette.value))
</script>

<template>
  <section class="page-flow page-flow--settings settings-page">
    <header class="settings-intro">
      <div>
        <p class="eyebrow">偏好设置</p>
        <h2>外观</h2>
        <p class="hint">调整 PocketTally 的主题和配色，修改会立即应用并保存在当前浏览器中。</p>
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
        :ui="{ root: 'settings-theme-group', fieldset: 'settings-theme-options', item: 'settings-theme-option', wrapper: 'settings-theme-copy' }"
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
            <p>选择一套适合你的品牌色。每个选项都同时显示名称和色板。</p>
          </div>
          <span class="settings-current-palette">当前：{{ selectedPalette?.label }}</span>
        </div>
      </template>
      <div class="palette-grid" aria-label="配色预设">
        <UButton
          v-for="item in APPEARANCE_PALETTES"
          :key="item.value"
          class="palette-choice"
          :class="{ 'palette-choice--selected': workspace.palette.value === item.value }"
          color="neutral"
          variant="outline"
          :aria-pressed="workspace.palette.value === item.value"
          :aria-label="`选择${item.label}配色，${item.description}`"
          @click="workspace.palette.value = item.value"
        >
          <span class="palette-swatch" aria-hidden="true">
            <i :style="{ backgroundColor: item.preview[0] }" />
            <i :style="{ backgroundColor: item.preview[1] }" />
          </span>
          <span class="palette-choice-copy">
            <strong>{{ item.label }}</strong>
            <small>{{ item.description }}</small>
          </span>
          <UIcon v-if="workspace.palette.value === item.value" name="i-lucide-check" class="palette-choice-check" aria-hidden="true" />
        </UButton>
      </div>
      <p class="settings-selection-status" role="status">已选择「{{ selectedPalette?.label }}」配色</p>
    </UCard>
  </section>
</template>
