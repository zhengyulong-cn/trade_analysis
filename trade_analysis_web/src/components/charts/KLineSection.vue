<script setup lang="ts">
import type { ChartOptions, DeepPartial } from 'lightweight-charts'
import { computed } from 'vue'
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
    contractLoading?: boolean
    contractDisabled?: boolean
    periodDisabled?: boolean
    canBuildSegments?: boolean
    canLoadSegments?: boolean
    autoLoadSegments?: boolean
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
    canBuildSegments: true,
    canLoadSegments: true,
    autoLoadSegments: false,
    contractPlaceholder: '请选择合约',
    segmentLines: () => [],
    summaryItems: () => [],
    chartOptions: () => ({}),
    emptyDescription: '暂无 K 线数据',
    unavailableDescription: '暂无可用数据',
  },
)

const hasChartData = computed(() => props.chartData.kLineList.length > 0)
const hasContractList = computed(() => props.contractOptions.length > 0)
const hasToolbar = computed(() => props.periodOptions.length > 0)

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
      <header class="header-info">
        <div v-if="hasToolbar" class="header-actions">
          <el-radio-group
            :model-value="selectedPeriod"
            class="period-group"
            :disabled="periodDisabled"
            @update:model-value="handlePeriodChange"
          >
            <el-radio-button
              v-for="period in periodOptions"
              :key="period.value"
              :value="period.value"
            >
              {{ period.label }}
            </el-radio-button>
          </el-radio-group>
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

      <div class="chart-layout">
        <div
          v-if="hasContractList"
          class="contract-list"
          :class="{ 'contract-list--loading': contractLoading }"
        >
          <div
            v-for="contract in contractOptions"
            :key="contract.value"
            class="contract-list-item"
            :class="{ 'contract-list-item--active': contract.value === selectedContract }"
            :disabled="contractDisabled"
            @click="handleContractChange(contract.value)"
          >
            <span class="contract-list-symbol">{{ contract.value }}</span>
            <span v-if="contract.description" class="contract-list-name">
              {{ contract.description }}
            </span>
          </div>
        </div>

        <div class="chart-card">
          <KLineChart
            v-if="hasChartData"
            :data="chartData"
            :segment-lines="segmentLines"
            :can-build-segments="canBuildSegments"
            :can-load-segments="canLoadSegments"
            :auto-load-segments="autoLoadSegments"
            :common-chart-options="chartOptions"
            @crosshair-move="handleCrosshairMove"
            @segment-line-change="handleSegmentLineChange"
            @segment-line-create="handleSegmentLineCreate"
            @segment-line-delete="handleSegmentLineDelete"
            @segment-build-request="handleSegmentBuildRequest"
            @segment-load-request="handleSegmentLoadRequest"
            @segment-auto-load-toggle="handleSegmentAutoLoadToggle"
          />
          <el-empty v-else class="chart-empty" :description="emptyDescription" />
        </div>
      </div>
    </template>

    <el-empty v-else :description="unavailableDescription" />
  </section>
</template>

<style lang="less" scoped>
.chart-section {
  min-height: 40rem;
  padding: 16px;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);

  .header-info {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 14px;

    .header-actions {
      flex: 0 0 auto;
    }

    .summary-bar {
      display: flex;
      align-items: center;
      flex-wrap: nowrap;
      gap: 8px;
      margin-left: auto;
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

.chart-layout {
  display: flex;
  gap: .75rem;
  align-items: stretch;
}

.contract-list {
  width: 8rem;
  flex: 0 0 180px;
  display: flex;
  flex-direction: column;
  gap: .5rem;
  max-height: 38rem;
  padding-right: 4px;
  overflow-y: auto;
}

.contract-list--loading {
  opacity: 0.72;
}

.contract-list-item {
  padding: 0.75rem;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
  color: #303133;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 4px;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    background-color 0.2s ease,
    box-shadow 0.2s ease,
    color 0.2s ease;
}

.contract-list-item:hover:not(:disabled) {
  border-color: #c6e2ff;
  background: #f7fbff;
}

.contract-list-item:disabled {
  cursor: not-allowed;
  opacity: 0.68;
}

.contract-list-item--active {
  border-color: #409eff;
  background: #ecf5ff;
  box-shadow: inset 0 0 0 1px rgba(64, 158, 255, 0.18);
}

.contract-list-symbol {
  font-size: 14px;
  font-weight: 600;
  line-height: 1.2;
}

.contract-list-name {
  color: #909399;
  font-size: 12px;
  line-height: 1.4;
}

.chart-card {
  flex: 1;
  min-width: 0;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  overflow: hidden;
}

.chart-empty {
  min-height: 640px;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 640px) {
  .chart-section {
    padding: 12px;
  }

  .header-info {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    justify-content: flex-start;
  }

  .summary-bar {
    gap: 8px;
    margin-left: 0;
  }

  .summary-item {
    border-radius: 999px;
  }

  .chart-layout {
    flex-direction: column;
  }

  .contract-list {
    width: 100%;
    flex: initial;
    max-height: none;
    padding-right: 0;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
  }
}
</style>
