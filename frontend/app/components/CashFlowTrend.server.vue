<script setup lang="ts">
import type { CashFlowBucket, Granularity } from '~/types/ledger'

defineProps<{
  buckets: CashFlowBucket[]
  granularity: Granularity
  variant: 'compact' | 'full'
}>()
</script>

<template>
  <div class="cash-flow-trend cash-flow-trend--placeholder" :class="`cash-flow-trend--${variant}`" aria-label="现金流趋势正在加载" role="img">
    <div class="cash-flow-placeholder-grid" aria-hidden="true">
      <USkeleton v-for="index in variant === 'full' ? 8 : 5" :key="index" aria-hidden="true" class="cash-flow-placeholder-bar motion-reduce:animate-none" />
    </div>
  </div>
</template>

<style scoped>
.cash-flow-trend--placeholder {
  min-width: 0;
  height: 280px;
}

.cash-flow-trend--compact.cash-flow-trend--placeholder {
  height: 190px;
}

.cash-flow-placeholder-grid {
  display: flex;
  align-items: end;
  justify-content: space-around;
  gap: 10px;
  height: 100%;
  padding: 24px 12px;
  border-radius: 10px;
  background: var(--ui-bg-muted);
}

.cash-flow-placeholder-bar {
  width: 9%;
  height: 45%;
}

.cash-flow-placeholder-bar:nth-child(2n) {
  height: 68%;
}
</style>
