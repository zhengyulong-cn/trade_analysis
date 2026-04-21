<script setup lang="ts">
import {
  CandlestickSeries,
  ColorType,
  createChart,
  type ChartOptions,
  type DeepPartial,
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
let crosshairMoveHandler: ((param: any) => void) | null = null;

const resizeHandler = () => {
  if (!chart || !chartContainer.value) return;
  const dimensions = chartContainer.value.getBoundingClientRect();
  chart.resize(dimensions.width, dimensions.height);
};

const applyChartData = () => {
  if (!kSeries) return;
  kSeries.setData(props.data.kLineList ?? []);
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
  window.removeEventListener("resize", resizeHandler);
});

defineExpose({
  getChart: () => chart,
  getKSeries: () => kSeries,
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
  <div class="lw-chart" ref="chartContainer"></div>
</template>

<style lang="less" scoped>
.lw-chart {
  width: 100%;
  height: 560px;
  position: relative;
}
</style>
