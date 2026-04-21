<script setup lang="ts">
import {
  CandlestickSeries,
  ColorType,
  createChart,
  LineSeries,
  type ChartOptions,
  type DeepPartial,
  type LineData,
  type IChartApi,
} from "lightweight-charts";
import { onMounted, onUnmounted, ref, watch } from "vue";

interface KLineItem {
  time: number
  open: number
  high: number
  low: number
  close: number
}

const props = withDefaults(
  defineProps<{
    data: {
      kLineList: KLineItem[]
    }
    autosize?: boolean
    commonChartOptions?: DeepPartial<ChartOptions>
  }>(),
  {
    autosize: true,
    commonChartOptions: () => ({}),
  }
);

const emit = defineEmits<{
  'crosshair-move': [value: KLineItem | null]
}>()

const chartContainer = ref<HTMLDivElement | null>(null);
let chart: IChartApi | null = null;
let kSeries: any = null;
let ema20Series: any = null;
let ema120Series: any = null;
let crosshairMoveHandler: ((param: any) => void) | null = null;

const calculateEmaData = (kLineList: KLineItem[], period: number): LineData<number>[] => {
  if (kLineList.length < period) {
    return [];
  }

  const multiplier = 2 / (period + 1);
  const initialSum = kLineList
    .slice(0, period)
    .reduce((sum, item) => sum + item.close, 0);
  let previousEma = initialSum / period;
  const initialItem = kLineList[period - 1];

  if (!initialItem) {
    return [];
  }

  const emaData: LineData<number>[] = [
    {
      time: initialItem.time,
      value: Number(previousEma.toFixed(4)),
    },
  ];

  for (let index = period; index < kLineList.length; index += 1) {
    const item = kLineList[index];
    if (!item) {
      continue;
    }

    previousEma = (item.close - previousEma) * multiplier + previousEma;
    emaData.push({
      time: item.time,
      value: Number(previousEma.toFixed(4)),
    });
  }

  return emaData;
};

const resizeHandler = () => {
  if (!chart || !chartContainer.value) return;
  const dimensions = chartContainer.value.getBoundingClientRect();
  chart.resize(dimensions.width, dimensions.height);
};

const applyChartData = () => {
  if (!kSeries) return;
  const kLineList = props.data.kLineList ?? [];
  kSeries.setData(kLineList);
  ema20Series?.setData(calculateEmaData(kLineList, 20));
  ema120Series?.setData(calculateEmaData(kLineList, 120));
  chart?.timeScale().fitContent();
};

const getCrosshairKLine = (param: any): KLineItem | null => {
  if (!kSeries || !param?.time) {
    return null
  }

  const seriesData = param.seriesData?.get(kSeries)
  if (!seriesData) {
    return null
  }

  const time = typeof seriesData.time === "number" ? seriesData.time : param.time
  const open = Number(seriesData.open)
  const high = Number(seriesData.high)
  const low = Number(seriesData.low)
  const close = Number(seriesData.close)

  if (![time, open, high, low, close].every(Number.isFinite)) {
    return null
  }

  return {
    time: Number(time),
    open,
    high,
    low,
    close,
  }
}

onMounted(() => {
  if (!chartContainer.value) return;

  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: chartContainer.value.clientHeight || 560,
    layout: {
      background: { type: ColorType.Solid, color: "#ffffff" },
      textColor: "#606266",
    },
    ...props.commonChartOptions,
  });

  const chartInstance = chart as any;
  kSeries =
    typeof chartInstance.addCandlestickSeries === "function"
      ? chartInstance.addCandlestickSeries({
          upColor: "#f56c6c",
          downColor: "#67c23a",
          borderUpColor: "#f56c6c",
          borderDownColor: "#67c23a",
          wickUpColor: "#f56c6c",
          wickDownColor: "#67c23a",
        })
      : chartInstance.addSeries(CandlestickSeries, {
          upColor: "#f56c6c",
          downColor: "#67c23a",
          borderUpColor: "#f56c6c",
          borderDownColor: "#67c23a",
          wickUpColor: "#f56c6c",
          wickDownColor: "#67c23a",
        });

  ema20Series =
    typeof chartInstance.addLineSeries === "function"
      ? chartInstance.addLineSeries({
          title: "EMA20",
          color: "#ff30d4",
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: true,
        })
      : chartInstance.addSeries(LineSeries, {
          title: "EMA20",
          color: "#ff30d4",
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: true,
        });

  ema120Series =
    typeof chartInstance.addLineSeries === "function"
      ? chartInstance.addLineSeries({
          title: "EMA120",
          color: "#1811ff",
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: true,
        })
      : chartInstance.addSeries(LineSeries, {
          title: "EMA120",
          color: "#1811ff",
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: true,
        });

  applyChartData();
  resizeHandler();

  crosshairMoveHandler = (param) => {
    emit('crosshair-move', getCrosshairKLine(param));
  };
  chart.subscribeCrosshairMove(crosshairMoveHandler);

  if (props.autosize) {
    window.addEventListener("resize", resizeHandler);
  }
});

onUnmounted(() => {
  if (chart && crosshairMoveHandler) {
    chart.unsubscribeCrosshairMove(crosshairMoveHandler);
    crosshairMoveHandler = null;
  }
  if (chart) {
    chart.remove();
    chart = null;
  }
  if (kSeries) {
    kSeries = null;
  }
  if (ema20Series) {
    ema20Series = null;
  }
  if (ema120Series) {
    ema120Series = null;
  }
  window.removeEventListener("resize", resizeHandler);
});

defineExpose({
  getChart: () => chart,
  getKSeries: () => kSeries,
  getEma20Series: () => ema20Series,
  getEma120Series: () => ema120Series,
});

watch(
  () => props.autosize,
  (enabled) => {
    if (!enabled) {
      window.removeEventListener("resize", resizeHandler);
      return;
    }
    window.addEventListener("resize", resizeHandler);
  }
);

watch(
  () => props.commonChartOptions,
  (newOptions) => {
    if (!chart) return;
    chart.applyOptions(newOptions);
  },
  { deep: true }
);

watch(
  () => props.data.kLineList,
  () => {
    applyChartData();
    emit('crosshair-move', null);
  },
  { deep: true }
);
</script>

<template>
  <div class="lw-chart-wrap">
    <div class="lw-chart" ref="chartContainer"></div>
    <div class="ema-legend">
      <span class="ema-legend__item ema-legend__item--ema20">EMA20</span>
      <span class="ema-legend__item ema-legend__item--ema120">EMA120</span>
    </div>
  </div>
</template>

<style lang="less" scoped>
.lw-chart-wrap {
  width: 100%;
  height: 560px;
  position: relative;
}

.lw-chart {
  width: 100%;
  height: 100%;
  position: relative;
}

.ema-legend {
  position: absolute;
  top: 10px;
  left: 12px;
  z-index: 1;
  display: flex;
  gap: 12px;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.86);
  color: #303133;
  font-size: 12px;
  line-height: 1;
  pointer-events: none;

  .ema-legend__item {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    white-space: nowrap;
  }

  .ema-legend__item::before {
    content: "";
    width: 16px;
    height: 2px;
    border-radius: 999px;
  }

  .ema-legend__item--ema20::before {
    background: #f59e0b;
  }

  .ema-legend__item--ema120::before {
    background: #7c3aed;
  }
}
</style>
