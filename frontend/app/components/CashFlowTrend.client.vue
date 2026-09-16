<script setup lang="ts">
import {
  VisAxis,
  VisCrosshair,
  VisLine,
  VisScatter,
  VisStackedBar,
  VisTooltip,
  VisXYContainer,
  VisStackedBarSelectors,
} from '@unovis/vue'
import { FillPatternType, CrosshairSnapMode } from '@unovis/ts'
import type { CashFlowBucket, Granularity } from '~/types/ledger'
import {
  bucketDateFormat,
  cashFlowChartRows,
  cashFlowScale,
  cashFlowSummary,
  clampSelectedIndex,
  sampleBucketIndexes,
  type CashFlowChartRow,
} from '~/utils/cashFlowTrend'
import { localInput, money } from '~/utils/money'

const props = defineProps<{
  buckets: CashFlowBucket[]
  granularity: Granularity
  variant: 'compact' | 'full'
}>()

const emit = defineEmits<{ drilldown: [startAt: string, endAt: string] }>()
const selectedIndex = ref(-1)
const chartFocused = ref(false)
const tableOpen = ref(false)
const reducedMotion = ref(import.meta.client && window.matchMedia('(prefers-reduced-motion: reduce)').matches)
const chartDuration = computed(() => reducedMotion.value ? 0 : 160)
let motionQuery: MediaQueryList | undefined

const rows = computed(() => cashFlowChartRows(props.buckets))
const selected = computed(() => rows.value[selectedIndex.value])
const summary = computed(() => cashFlowSummary(props.buckets))
const hasFlowData = computed(() => summary.value.incomeAmountMinor + summary.value.refundAmountMinor + summary.value.expenseAmountMinor !== 0)
const scale = computed(() => cashFlowScale(props.buckets))
const selectedX = computed(() => selected.value?.x)
const labelIndexes = computed(() => sampleBucketIndexes(rows.value.length, props.variant === 'full' ? 8 : 6))

const x = (row: CashFlowChartRow) => row.x
const barY = [
  (row: CashFlowChartRow) => row.income,
  (row: CashFlowChartRow) => row.refund,
  (row: CashFlowChartRow) => row.expense,
]
const netY = (row: CashFlowChartRow) => row.net
const barColor = (_row: CashFlowChartRow, _index: number, key?: string) => ({
  income: 'var(--pt-chart-income)',
  refund: 'var(--pt-chart-refund)',
  expense: 'var(--pt-chart-expense)',
}[key || ''] || 'var(--pt-chart-income)')
const chartEvents = {
  [VisStackedBarSelectors.bar]: {
    click: (_row: CashFlowChartRow, _event: MouseEvent, index: number) => selectIndex(index),
  },
}
const chartAttributes = {
  [VisStackedBarSelectors.barGroup]: {
    'data-cash-flow-index': (row: CashFlowChartRow) => rows.value.indexOf(row),
  },
}

function selectIndex(index: number) {
  selectedIndex.value = clampSelectedIndex(index, rows.value.length)
}

function selectNext(offset: number) {
  if (!rows.value.length) return
  selectIndex(selectedIndex.value < 0 ? rows.value.length - 1 : selectedIndex.value + offset)
}

function keydown(event: KeyboardEvent) {
  if (event.key === 'ArrowLeft') { event.preventDefault(); selectNext(-1) }
  if (event.key === 'ArrowRight') { event.preventDefault(); selectNext(1) }
  if (event.key === 'Home') { event.preventDefault(); selectIndex(0) }
  if (event.key === 'End') { event.preventDefault(); selectIndex(rows.value.length - 1) }
  if ((event.key === 'Enter' || event.key === ' ') && selected.value) {
    event.preventDefault()
    emit('drilldown', selected.value.startAt, selected.value.endAt)
  }
}

function chooseFromCrosshair(_x: number | Date | undefined, _datum: CashFlowChartRow | undefined, index: number | undefined) {
  if (index !== undefined) selectIndex(index)
}

function tooltipContent(value: CashFlowChartRow | { datum: CashFlowChartRow }) {
  const row = 'datum' in value ? value.datum : value
  const element = document.createElement('div')
  element.className = 'cash-flow-tooltip'
  element.innerHTML = `<strong>${bucketDateFormat(props.granularity, row.startAt, row.endAt)}</strong><span>收入 ${money(row.incomeAmountMinor)}</span><span>退款流入 ${money(row.refundAmountMinor)}</span><span>支出流出 ${money(row.expenseAmountMinor)}</span><span>净现金流 ${money(row.netCashFlowMinor)}</span>`
  return element
}

function xTickFormat(value: number) {
  const index = rows.value.findIndex(row => row.x === value)
  if (index < 0 || !labelIndexes.value.includes(index)) return ''
  return localInput(new Date(value).toISOString()).slice(props.granularity === 'day' ? 5 : 0, 10)
}

function updateReducedMotion(event?: MediaQueryListEvent) {
  reducedMotion.value = event?.matches ?? motionQuery?.matches ?? false
}

onMounted(() => {
  motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
  updateReducedMotion()
  motionQuery.addEventListener?.('change', updateReducedMotion)
})

onBeforeUnmount(() => {
  motionQuery?.removeEventListener?.('change', updateReducedMotion)
})

watch(() => props.buckets, (next) => {
  selectedIndex.value = next.length ? clampSelectedIndex(selectedIndex.value < 0 ? next.length - 1 : selectedIndex.value, next.length) : -1
}, { deep: true, immediate: true })
</script>

<template>
  <div class="cash-flow-trend" :class="`cash-flow-trend--${variant}`">
    <div class="cash-flow-legend" aria-label="图例">
      <span><i class="cash-flow-legend-mark cash-flow-legend-mark--income" />收入（流入）</span>
      <span><i class="cash-flow-legend-mark cash-flow-legend-mark--refund" />退款（流入）</span>
      <span><i class="cash-flow-legend-mark cash-flow-legend-mark--expense" />支出（流出）</span>
      <span><i class="cash-flow-legend-mark cash-flow-legend-mark--net" />净现金流（折线）</span>
    </div>

    <div v-if="!rows.length" class="empty-state cash-flow-empty">当前范围暂无现金流</div>
    <div v-else-if="!hasFlowData" class="empty-state cash-flow-empty">本期没有现金流变化</div>
    <div v-else class="cash-flow-chart-shell">
      <div
        class="cash-flow-chart"
        :data-reduced-motion="reducedMotion"
        :data-chart-duration="chartDuration"
        tabindex="0"
        role="application"
        aria-label="现金流趋势图，可使用方向键选择时间段"
        @focus="chartFocused = true"
        @blur="chartFocused = false"
        @keydown="keydown"
      >
        <VisXYContainer
          :data="rows"
          :height="variant === 'full' ? 280 : 190"
          :y-domain="scale"
          :prevent-empty-domain="true"
          aria-label="现金流趋势图"
        >
          <VisStackedBar
            :x="x"
            :y="barY"
            :color="barColor"
            :color-keys="['income', 'refund', 'expense']"
            :pattern="(_row, index) => index === 1 ? FillPatternType.StripesDiagonal : undefined"
            :bar-max-width="variant === 'full' ? 34 : 28"
            :bar-padding="0.22"
            :rounded-corners="3"
            :duration="chartDuration"
            :events="chartEvents"
            :attributes="chartAttributes"
          />
          <VisLine :x="x" :y="netY" color="var(--ui-text-highlighted)" :line-width="3" :duration="chartDuration" />
          <VisScatter :x="x" :y="netY" color="var(--ui-text-highlighted)" :size="8" :duration="chartDuration" />
          <VisAxis type="x" :tick-format="xTickFormat" :num-ticks="labelIndexes.length" />
          <VisAxis type="y" :tick-format="(value: number) => money(value)" />
          <VisCrosshair
            :snap-mode="CrosshairSnapMode.X"
            :force-show-at="chartFocused ? selectedX : undefined"
            :on-crosshair-move="chooseFromCrosshair"
            :show-horizontal-line="true"
            :circle-radius="4"
          />
          <VisTooltip
            :triggers="{ [VisStackedBarSelectors.bar]: (row: CashFlowChartRow) => tooltipContent(row) }"
            :follow-cursor="true"
          />
        </VisXYContainer>
      </div>
      <div v-if="selected" class="cash-flow-detail" aria-live="polite">
        <div class="cash-flow-detail-heading">
          <div><span class="hint">时间段</span><strong>{{ bucketDateFormat(granularity, selected.startAt, selected.endAt) }}</strong></div>
          <UButton label="查看该时段流水" color="neutral" variant="outline" size="sm" @click="emit('drilldown', selected.startAt, selected.endAt)" />
        </div>
        <dl>
          <div><dt>普通收入</dt><dd>{{ money(selected.incomeAmountMinor) }}</dd></div>
          <div><dt>退款流入</dt><dd>{{ money(selected.refundAmountMinor) }}</dd></div>
          <div><dt>支出流出</dt><dd>{{ money(selected.expenseAmountMinor) }}</dd></div>
          <div><dt>净现金流</dt><dd>{{ money(selected.netCashFlowMinor) }}</dd></div>
        </dl>
      </div>
    </div>

    <UCollapsible v-if="variant === 'full' && rows.length" v-model:open="tableOpen" class="cash-flow-table-wrap" :ui="{ content: 'motion-reduce:animate-none motion-reduce:transition-none' }">
      <UButton class="cash-flow-table-trigger" color="neutral" variant="ghost" :label="tableOpen ? '收起完整数据表' : '查看完整数据表'" :aria-expanded="tableOpen" />
      <template #content>
        <div class="cash-flow-table-scroll">
          <table>
            <caption class="sr-only">现金流趋势完整数据</caption>
            <thead><tr><th scope="col">时间范围</th><th scope="col">收入</th><th scope="col">退款</th><th scope="col">支出</th><th scope="col">净额</th></tr></thead>
            <tbody><tr v-for="row in rows" :key="row.startAt"><th scope="row">{{ bucketDateFormat(granularity, row.startAt, row.endAt) }}</th><td>{{ money(row.incomeAmountMinor) }}</td><td>{{ money(row.refundAmountMinor) }}</td><td>{{ money(row.expenseAmountMinor) }}</td><td>{{ money(row.netCashFlowMinor) }}</td></tr></tbody>
          </table>
        </div>
      </template>
    </UCollapsible>
  </div>
</template>

<style scoped>
.cash-flow-trend {
  min-width: 0;
}

.cash-flow-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  margin-bottom: 12px;
  color: var(--pt-chart-axis);
  font-size: var(--text-xs);
  line-height: var(--text-xs--line-height);
}

.cash-flow-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.cash-flow-legend-mark {
  display: inline-block;
  width: 12px;
  height: 8px;
  border-radius: 2px;
  background: var(--pt-chart-income);
}

.cash-flow-legend-mark--refund {
  background: repeating-linear-gradient(135deg, var(--pt-chart-refund) 0 3px, transparent 3px 5px), var(--pt-chart-refund);
}

.cash-flow-legend-mark--expense {
  background: var(--pt-chart-expense);
}

.cash-flow-legend-mark--net {
  width: 16px;
  height: 3px;
  border-radius: 0;
  background: var(--ui-text-highlighted);
}

.cash-flow-chart-shell {
  display: grid;
  gap: 14px;
}

.cash-flow-chart {
  min-width: 0;
  height: 280px;
  border-radius: 10px;
  --vis-axis-tick-label-text-color: var(--pt-chart-axis);
  --vis-axis-domain-line-color: var(--pt-chart-axis);
  --vis-axis-grid-line-color: var(--pt-chart-grid);
  --vis-crosshair-line-stroke-color: var(--pt-focus-ring);
  --vis-crosshair-circle-stroke-color: var(--ui-bg);
  --vis-tooltip-background-color: var(--ui-bg-elevated);
  --vis-tooltip-border-color: var(--ui-border-muted);
  --vis-tooltip-text-color: var(--ui-text);
}

.cash-flow-trend--compact .cash-flow-chart {
  height: 190px;
}

.cash-flow-chart :deep(.unovis-xy-container) {
  width: 100%;
  height: 100%;
}

.cash-flow-chart :deep(svg) {
  overflow: visible;
}

.cash-flow-detail {
  border-top: 1px solid var(--ui-border-muted);
  padding-top: 12px;
}

.cash-flow-detail-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 12px;
}

.cash-flow-detail-heading > div {
  display: grid;
  gap: 3px;
}

.cash-flow-detail-heading strong {
  font-size: var(--text-sm);
  line-height: var(--text-sm--line-height);
}

.cash-flow-detail dl {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin: 12px 0 0;
}

.cash-flow-detail dl > div {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.cash-flow-detail dt {
  color: var(--ui-text-muted);
  font-size: var(--text-xs);
  line-height: var(--text-xs--line-height);
}

.cash-flow-detail dd {
  margin: 0;
  overflow-wrap: anywhere;
  font-size: var(--text-sm);
  line-height: var(--text-sm--line-height);
  font-variant-numeric: tabular-nums;
}

.cash-flow-table-wrap {
  margin-top: 14px;
  border-top: 1px solid var(--ui-border-muted);
  padding-top: 8px;
}

.cash-flow-table-trigger {
  padding-inline: 0;
}

.cash-flow-table-scroll {
  overflow-x: auto;
  margin-top: 8px;
}

.cash-flow-table-scroll table {
  width: 100%;
  min-width: 620px;
  border-collapse: collapse;
  font-size: var(--text-xs);
  line-height: var(--text-xs--line-height);
}

.cash-flow-table-scroll th,
.cash-flow-table-scroll td {
  border-bottom: 1px solid var(--ui-border-muted);
  padding: 9px 8px;
  text-align: right;
  white-space: nowrap;
}

.cash-flow-table-scroll th:first-child,
.cash-flow-table-scroll td:first-child {
  text-align: left;
}

.cash-flow-table-scroll thead th {
  color: var(--ui-text-muted);
  font-weight: 600;
}

.cash-flow-empty {
  padding-block: 28px;
}

.cash-flow-tooltip {
  display: grid;
  gap: 4px;
  min-width: 150px;
  padding: 4px;
  color: var(--ui-text);
  font-size: var(--text-xs);
  line-height: var(--text-xs--line-height);
}

.cash-flow-tooltip strong {
  margin-bottom: 2px;
}

@media (max-width: 560px) {
  .cash-flow-chart {
    height: 220px;
  }

  .cash-flow-trend--compact .cash-flow-chart {
    height: 170px;
  }

  .cash-flow-detail-heading {
    align-items: stretch;
    flex-direction: column;
  }

  .cash-flow-detail-heading button {
    align-self: flex-start;
  }

  .cash-flow-detail dl {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (prefers-reduced-motion: reduce) {
  .cash-flow-chart :deep([animating]) {
    transition: none !important;
  }
}
</style>
