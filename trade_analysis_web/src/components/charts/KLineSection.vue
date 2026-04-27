<script setup lang="ts">
import type { ChartOptions, DeepPartial } from 'lightweight-charts'
import KLineChart from './KLineChart.vue'

interface KLineItem {
  time: number
  open: number
  high: number
  low: number
  close: number
  ema20?: number
  ema120?: number
}

interface ContractOption {
  label: string
  value: string
  description?: string
  isFavorite?: boolean
}

interface PeriodOption {
  label: string
  value: number | string
}

interface SegmentLineItem {
  id: string
  points: Array<{
    time: number
    value: number
  }>
  lineStyle?: 'solid' | 'dashed'
  segmentRole?: string
  segmentIndex?: number
  direction?: string
}

interface SegmentLineChange {
  segment: SegmentLineItem
  endpoint: 'start' | 'end'
  points: Array<{
    time: number
    value: number
  }>
}

interface SegmentLineCreate {
  startPoint: {
    time: number
    value: number
  }
  endPoint: {
    time: number
    value: number
  }
}

interface SegmentLineDelete {
  segment: SegmentLineItem
}

const emit = defineEmits<{
  'update:selectedContract': [value: string]
  'update:selectedPeriod': [value: number | string]
  'hoverKlineChange': [value: KLineItem | null]
  'segmentLineChange': [value: SegmentLineChange]
  'segmentLineCreate': [value: SegmentLineCreate]
  'segmentLineDelete': [value: SegmentLineDelete]
  'segmentBuildRequest': []
  'segmentLoadRequest': []
  'segmentAutoLoadToggle': []
}>()

const props = withDefaults(
  defineProps<{
    loading?: boolean
    available?: boolean
    selectedContract?: string
    selectedPeriod?: number | string
    contractOptions?: ContractOption[]
    periodOptions?: PeriodOption[]
    canBuildSegments?: boolean
    canLoadSegments?: boolean
    autoLoadSegments?: boolean
    chartData: {
      symbol?: string
      name?: string
      kLineList: KLineItem[]
    }
    segmentLines?: SegmentLineItem[]
    chartOptions?: DeepPartial<ChartOptions>
    emptyDescription?: string
    unavailableDescription?: string
  }>(),
  {
    loading: false,
    available: true,
    selectedContract: '',
    selectedPeriod: '',
    contractOptions: () => [],
    periodOptions: () => [],
    canBuildSegments: true,
    canLoadSegments: true,
    autoLoadSegments: false,
    segmentLines: () => [],
    chartOptions: () => ({}),
    emptyDescription: '暂无 K 线数据',
    unavailableDescription: '暂无可用数据',
  },
)

const handleSelectedContractChange = (value: string) => {
  emit('update:selectedContract', value)
}

const handleSelectedPeriodChange = (value: number | string) => {
  emit('update:selectedPeriod', value)
}

const handleCrosshairMove = (value: KLineItem | null) => {
  emit('hoverKlineChange', value)
}

const handleSegmentLineChange = (value: SegmentLineChange) => {
  emit('segmentLineChange', value)
}

const handleSegmentLineCreate = (value: SegmentLineCreate) => {
  emit('segmentLineCreate', value)
}

const handleSegmentLineDelete = (value: SegmentLineDelete) => {
  emit('segmentLineDelete', value)
}

const handleSegmentBuildRequest = () => {
  emit('segmentBuildRequest')
}

const handleSegmentLoadRequest = () => {
  emit('segmentLoadRequest')
}

const handleSegmentAutoLoadToggle = () => {
  emit('segmentAutoLoadToggle')
}
</script>

<template>
  <section v-loading="loading" class="chart-section">
    <template v-if="available">
      <div class="chart-card">
        <KLineChart
          :data="chartData"
          :selected-contract="selectedContract"
          :selected-period="selectedPeriod"
          :contract-options="contractOptions"
          :period-options="periodOptions"
          :segment-lines="segmentLines"
          :can-build-segments="canBuildSegments"
          :can-load-segments="canLoadSegments"
          :auto-load-segments="autoLoadSegments"
          :common-chart-options="chartOptions"
          @update:selected-contract="handleSelectedContractChange"
          @update:selected-period="handleSelectedPeriodChange"
          @crosshair-move="handleCrosshairMove"
          @segment-line-change="handleSegmentLineChange"
          @segment-line-create="handleSegmentLineCreate"
          @segment-line-delete="handleSegmentLineDelete"
          @segment-build-request="handleSegmentBuildRequest"
          @segment-load-request="handleSegmentLoadRequest"
          @segment-auto-load-toggle="handleSegmentAutoLoadToggle"
        />
      </div>
    </template>
    <el-empty v-else :description="unavailableDescription" />
  </section>
</template>

<style lang="less" scoped>
.chart-section {
  min-height: 40rem;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.chart-card {
  min-width: 0;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  overflow: hidden;
}

@media (max-width: 640px) {
  .chart-section {
    padding: 12px;
  }
}
</style>
