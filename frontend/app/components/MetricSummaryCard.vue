<script setup lang="ts">
defineProps<{
  label: string
  value: string
  comparison?: string
  emphasis?: boolean
  icon?: string
}>()
</script>

<template>
  <UCard
    :class="['metric-summary-card', { 'metric-summary-card--emphasis': emphasis }]"
    variant="outline"
    :ui="{ root: 'min-w-0', body: 'p-4 sm:p-5' }"
  >
    <div class="metric-summary-card__header">
      <span>{{ label }}</span>
      <UIcon v-if="icon" :name="icon" aria-hidden="true" />
    </div>
    <strong>{{ value }}</strong>
    <p v-if="comparison">{{ comparison }}</p>
  </UCard>
</template>

<style scoped>
.metric-summary-card {
  min-width: 0;
}

.metric-summary-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: var(--ui-text-muted);
  font-size: 13px;
  font-weight: 600;
}

.metric-summary-card__header :deep(svg) {
  color: var(--ui-text-dimmed);
}

.metric-summary-card strong {
  display: block;
  margin-top: 10px;
  overflow-wrap: anywhere;
  font-size: clamp(1.35rem, 2vw, 1.85rem);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.03em;
}

.metric-summary-card p {
  margin: 5px 0 0;
  color: var(--ui-text-muted);
  font-size: 12px;
}

.metric-summary-card--emphasis {
  border-color: color-mix(in srgb, var(--ui-primary) 42%, var(--ui-border-muted));
  background: color-mix(in srgb, var(--ui-primary) 8%, var(--ui-bg-elevated));
}

.metric-summary-card--emphasis strong,
.metric-summary-card--emphasis .metric-summary-card__header :deep(svg) {
  color: var(--ui-primary);
}
</style>
