<script setup lang="ts">
import type { ChartOptions, DeepPartial } from 'lightweight-charts'
import { computed } from 'vue'
import FutureContractIntervalSelector from '@/components/futures/FutureContractIntervalSelector.vue'
import KLineChart from './KLineChart.vue'

interface KLineItem {
  time: number
  open: number
  high: number
  low: number
  close: number
}

interface SummaryItem {
  label: string
  value: string | number
  subvalue?: string
  wide?: boolean
  tone?: 'up' | 'down' | 'neutral'
}

interface ContractOption {
  label: string
  value: string
  description?: string
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
}>()

const props = withDefaults(
  defineProps<{
    loading?: boolean
    available?: boolean
    selectedContract?: string
    selectedPeriod?: number | string
    contractOptions?: ContractOption[]
    periodOptions?: PeriodOption[]
    contractLoading?: boolean
    contractDisabled?: boolean
    periodDisabled?: boolean
    contractPlaceholder?: string
    chartData: {
      kLineList: KLineItem[]
    }
    segmentLines?: SegmentLineItem[]
    summaryItems?: SummaryItem[]
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
    contractLoading: false,
    contractDisabled: false,
    periodDisabled: false,
    contractPlaceholder: '请选择合约',
    segmentLines: () => [],
    summaryItems: () => [],
    chartOptions: () => ({}),
    emptyDescription: '暂无 K 线数据',
    unavailableDescription: '暂无可用数据',
  },
)

const hasChartData = computed(() => props.chartData.kLineList.length > 0)
const hasToolbar = computed(() => props.contractOptions.length > 0 || props.periodOptions.length > 0)

const handleContractChange = (value: string) => {
  emit('update:selectedContract', value)
}

const handlePeriodChange = (value: number | string) => {
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
</script>

<template>
  <section v-loading="loading" class="chart-section">
    <template v-if="available">
      <header class="header-info">
        <div v-if="hasToolbar" class="header-actions">
          <FutureContractIntervalSelector
            :selected-contract="selectedContract"
            :selected-period="selectedPeriod"
            :contract-options="contractOptions"
            :period-options="periodOptions"
            :contract-loading="contractLoading"
            :contract-disabled="contractDisabled"
            :period-disabled="periodDisabled"
            :contract-placeholder="contractPlaceholder"
            @update:selected-contract="handleContractChange"
            @update:selected-period="handlePeriodChange"
          />
        </div>

        <div v-if="summaryItems.length" class="summary-bar">
          <div
            v-for="(item, index) in summaryItems"
            :key="`${item.label}-${index}`"
            class="summary-item"
            :class="{ 'summary-item--wide': item.wide }"
          >
            <span class="summary-label">{{ item.label }}</span>
            <strong
              class="summary-value"
              :class="{
                'summary-value--up': item.tone === 'up',
                'summary-value--down': item.tone === 'down',
                'summary-value--neutral': item.tone === 'neutral',
              }"
            >
              {{ item.value }}
            </strong>
            <span v-if="item.subvalue" class="summary-subvalue">{{ item.subvalue }}</span>
          </div>
        </div>
      </header>

      <div v-if="hasChartData" class="chart-card">
        <KLineChart
          :data="chartData"
          :segment-lines="segmentLines"
          :common-chart-options="chartOptions"
          @crosshair-move="handleCrosshairMove"
          @segment-line-change="handleSegmentLineChange"
          @segment-line-create="handleSegmentLineCreate"
          @segment-line-delete="handleSegmentLineDelete"
        />
      </div>
      <el-empty v-else :description="emptyDescription" />
    </template>

    <el-empty v-else :description="unavailableDescription" />
  </section>
</template>

<style lang="less" scoped>
.chart-section {
  min-height: 640px;
  padding: 16px;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);

  .header-info {
    display: flex;
    column-gap: 1rem;

    .header-actions {
      margin-bottom: 14px;
    }

    .summary-bar {
      display: flex;
      align-items: center;
      flex-wrap: nowrap;
      gap: 8px;
      margin-bottom: 14px;
      overflow-x: auto;
      scrollbar-width: thin;
      .summary-item {
        padding: 6px 12px;
        border-radius: 999px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        flex: 0 0 auto;
        max-width: none;
        .summary-label {
          color: #909399;
          font-size: 12px;
          white-space: nowrap;
        }

        .summary-value {
          color: #303133;
          font-size: 14px;
          line-height: 1;
          white-space: nowrap;
        }
        .summary-value--up {
          color: #f56c6c;
        }
        .summary-value--down {
          color: #67c23a;
        }
        .summary-value--neutral {
          color: #303133;
        }
        .summary-subvalue {
          color: #606266;
          font-size: 12px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
      }
      .summary-item--wide {
        padding-right: 14px;
      }
    }
  }
}

.chart-card {
  border: 1px solid #ebeef5;
  border-radius: 12px;
  overflow: hidden;
}

@media (max-width: 640px) {
  .chart-section {
    padding: 12px;
  }

  .header-actions {
    justify-content: flex-start;
  }

  .summary-bar {
    gap: 8px;
  }

  .summary-item {
    border-radius: 999px;
  }
}
</style>
