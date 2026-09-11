<script setup lang="ts">
import { APPEARANCE_PALETTES, type PaletteName, type ThemePreference } from '~/constants/appearance'
import type { MessageLevel } from '~/utils/messages'

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
const messages = useAppMessages()
const previewLevels: Array<{ level: MessageLevel; label: string; title: string; description: string }> = [
  { level: 'info', label: '触发信息', title: '信息示例', description: '这是一个短生命周期的信息 Toast，默认约 4 秒后消失。' },
  { level: 'success', label: '触发成功', title: '成功示例', description: '这是一个保存或操作成功后的 Toast，默认约 4 秒后消失。' },
  { level: 'warning', label: '触发警告', title: '警告示例', description: '这是一个较长生命周期的警告 Toast，默认约 8 秒后消失。' },
  { level: 'error', label: '触发错误', title: '错误示例', description: '这是一个需要持续处理的错误 UAlert，不会自动消失。' },
]

function previewMessageId(level: MessageLevel) {
  return `settings-message-preview-${level}`
}

function triggerPreview(item: typeof previewLevels[number]) {
  const id = previewMessageId(item.level)
  messages.push({
    id,
    level: item.level,
    title: item.title,
    description: item.description,
    persistent: item.level === 'error',
    action: item.level === 'error' ? { label: '再次触发', onSelect: () => triggerPreview(item) } : undefined,
  })
}

function clearPreviewMessages() {
  previewLevels.forEach(item => messages.dismiss(previewMessageId(item.level)))
}

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
            <p>选择一套适合你的品牌色。每个选项都同时显示名称和色板。</p>
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

    <UCard class="settings-card" variant="outline">
      <template #header>
        <div class="settings-card-heading">
          <div>
            <h3>消息反馈预览</h3>
            <p>手动触发各级别反馈，审阅 Toast、持久 UAlert、关闭按钮和操作按钮的效果。</p>
          </div>
          <UIcon name="i-lucide-message-square-more" aria-hidden="true" />
        </div>
      </template>
      <div class="settings-message-actions" aria-label="消息等级预览操作">
        <UButton
          v-for="item in previewLevels"
          :key="item.level"
          :color="item.level"
          variant="soft"
          :label="item.label"
          :aria-label="`${item.label}：${item.description}`"
          @click="triggerPreview(item)"
        />
        <UButton color="neutral" variant="outline" label="清空预览消息" @click="clearPreviewMessages" />
      </div>
      <UAlert color="neutral" variant="subtle" icon="i-lucide-eye" title="审阅提示" description="信息、成功和警告显示在右下角 Toast；错误显示在页面内容顶部并持续保留。切换亮色/暗色与八套配色可检查语义色 token。" />
    </UCard>
  </section>
</template>
