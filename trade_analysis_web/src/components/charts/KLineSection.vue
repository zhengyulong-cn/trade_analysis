<script setup lang="ts">
import type { ChartOptions, DeepPartial } from 'lightweight-charts'
import KLineChart from './KLineChart.vue'
import ChartSidebar from './sidebar_panel/ChartSidebar.vue'

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

const emit = defineEmits<{
  'update:selectedContract': [value: string]
  'update:selectedPeriod': [value: number | string]
  'hoverKlineChange': [value: KLineItem | null]
  'toggleFavorite': [value: string]
}>()

const props = withDefaults(
  defineProps<{
    loading?: boolean
    available?: boolean
    selectedContract?: string
    selectedPeriod?: number | string
    contractOptions?: ContractOption[]
    periodOptions?: PeriodOption[]
    chartData: {
      symbol?: string
      name?: string
      kLineList: KLineItem[]
    }
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

const handleToggleFavorite = (value: string) => {
  emit('toggleFavorite', value)
}
</script>

<template>
  <section v-loading="loading" class="chart-section">
    <template v-if="available">
      <div class="chart-box">
        <div class="chart-card">
          <KLineChart
            :data="chartData"
            :selected-contract="selectedContract"
            :selected-period="selectedPeriod"
            :contract-options="contractOptions"
            :period-options="periodOptions"
            :common-chart-options="chartOptions"
            @update:selected-contract="handleSelectedContractChange"
            @update:selected-period="handleSelectedPeriodChange"
            @crosshair-move="handleCrosshairMove"
          />
        </div>
        <div class="chart-sidebar">
          <ChartSidebar
            :contract-options="contractOptions"
            :selected-contract="selectedContract"
            @update:selected-contract="handleSelectedContractChange"
            @toggle-favorite="handleToggleFavorite"
          />
        </div>
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
.chart-box {
  display: flex;
  flex-direction: row;
  column-gap: .5rem;
  align-items: stretch;

  .chart-sidebar {
    flex: 0 0 auto;
    min-width: 0;
    box-sizing: border-box;
    border-left: 1px solid #ebeef5;
    border-radius: 12px;
    height: calc(100vh - 3.5rem);
  }

  .chart-card {
    min-width: 0;
    flex: 1;
    border: 1px solid #ebeef5;
    border-radius: 12px;
    overflow: hidden;
  }
}

@media (max-width: 640px) {
  .chart-section {
    padding: 12px;
  }

  .chart-box {
    flex-direction: column;

    .chart-sidebar {
      width: 100%;
    }
  }
}
</style>
