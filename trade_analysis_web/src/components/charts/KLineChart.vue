<script setup lang="ts">
import {
  CandlestickSeries,
  ColorType,
  createChart,
  LineStyle,
  LineSeries,
  type ChartOptions,
  type DeepPartial,
  type LineData,
  type IChartApi,
} from "lightweight-charts";
import { INITIAL_VISIBLE_K_LINE_COUNT } from "@/constants/chart";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import KLineChartContextMenu from './KLineChartContextMenu.vue'

interface KLineItem {
  time: number
  open: number
  high: number
  low: number
  close: number
}

interface SegmentLineItem {
  id: string
  points: LineData<number>[]
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

interface SegmentOverlayItem {
  id: string
  segment: SegmentLineItem
  x1: number
  y1: number
  x2: number
  y2: number
  isSelected: boolean
}

const props = withDefaults(
  defineProps<{
    data: {
      kLineList: KLineItem[]
    }
    segmentLines?: SegmentLineItem[]
    autosize?: boolean
    commonChartOptions?: DeepPartial<ChartOptions>
  }>(),
  {
    segmentLines: () => [],
    autosize: true,
    commonChartOptions: () => ({}),
  }
);

const emit = defineEmits<{
  'crosshair-move': [value: KLineItem | null]
  'segment-line-change': [value: SegmentLineChange]
  'segment-line-create': [value: SegmentLineCreate]
  'segment-line-delete': [value: SegmentLineDelete]
}>()

const chartContainer = ref<HTMLDivElement | null>(null);
let chart: IChartApi | null = null;
let kSeries: any = null;
let ema20Series: any = null;
let ema120Series: any = null;
let segmentSeriesList: any[] = [];
let crosshairMoveHandler: ((param: any) => void) | null = null;
let clickHandler: ((param: any) => void) | null = null;
let logicalRangeChangeHandler: (() => void) | null = null;
let timeScaleSizeChangeHandler: (() => void) | null = null;
let chartOptionsBeforeDrag: Pick<ChartOptions, 'handleScroll' | 'handleScale'> | null = null;

const selectedSegmentId = ref<string | null>(null);
const overlayItems = ref<SegmentOverlayItem[]>([]);
const overlaySize = ref({
  width: 0,
  height: 0,
});
const dragState = ref<{
  segmentId: string
  endpoint: 'start' | 'end'
  previewPoint: {
    time: number
    value: number
  }
} | null>(null);
const contextMenuState = ref<{
  visible: boolean
  x: number
  y: number
  startIndex: number | null
}>({
  visible: false,
  x: 0,
  y: 0,
  startIndex: null,
});

const overlayCursor = computed(() => (dragState.value ? 'grabbing' : 'default'));
const selectedSegment = computed(() => {
  if (!selectedSegmentId.value) {
    return null;
  }

  return props.segmentLines.find((segment) => segment.id === selectedSegmentId.value) ?? null;
});
const canCreateSegmentFromContext = computed(() => {
  const startIndex = contextMenuState.value.startIndex;
  return startIndex !== null && Boolean(props.data.kLineList[startIndex + 5]);
});
const canDeleteSelectedSegment = computed(() => selectedSegment.value?.segmentRole === 'confirmed');

const syncOverlaySize = () => {
  if (!chartContainer.value) {
    overlaySize.value = {
      width: 0,
      height: 0,
    };
    return;
  }

  const dimensions = chartContainer.value.getBoundingClientRect();
  overlaySize.value = {
    width: dimensions.width,
    height: dimensions.height,
  };
};

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
  syncOverlaySize();
  updateSegmentOverlayItems();
};

const applyVisibleRange = (kLineList: KLineItem[]) => {
  if (!chart) return;

  if (kLineList.length <= INITIAL_VISIBLE_K_LINE_COUNT) {
    chart.timeScale().fitContent();
    return;
  }

  chart.timeScale().setVisibleLogicalRange({
    from: kLineList.length - INITIAL_VISIBLE_K_LINE_COUNT,
    to: kLineList.length - 1,
  });
};

const applyChartData = () => {
  if (!kSeries) return;
  const kLineList = props.data.kLineList ?? [];
  kSeries.setData(kLineList);
  ema20Series?.setData(calculateEmaData(kLineList, 20));
  ema120Series?.setData(calculateEmaData(kLineList, 120));
  applySegmentLines();
  applyVisibleRange(kLineList);
};

const clearSegmentLines = () => {
  if (!chart || !segmentSeriesList.length) {
    segmentSeriesList = [];
    return;
  }

  for (const series of segmentSeriesList) {
    chart.removeSeries(series);
  }
  segmentSeriesList = [];
};

const createLineSeries = (chartInstance: any, options: Record<string, unknown>) => {
  return typeof chartInstance.addLineSeries === "function"
    ? chartInstance.addLineSeries(options)
    : chartInstance.addSeries(LineSeries, options);
};

const applySegmentLines = () => {
  if (!chart) {
    return;
  }

  clearSegmentLines();

  const chartInstance = chart as any;
  const segmentLines = props.segmentLines ?? [];
  for (const segment of segmentLines) {
    if (!segment.points?.length) {
      continue;
    }

    const lineSeries = createLineSeries(chartInstance, {
      title: segment.id,
      color: "#000000",
      lineWidth: 2,
      lineStyle:
        segment.lineStyle === "dashed" ? LineStyle.Dashed : LineStyle.Solid,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });
    lineSeries.setData(segment.points);
    segmentSeriesList.push(lineSeries);
  }

  updateSegmentOverlayItems();
};

const getSegmentDisplayPoints = (segment: SegmentLineItem) => {
  const points = segment.points.map((point) => ({
    time: Number(point.time),
    value: Number(point.value ?? 0),
  }));
  const preview = dragState.value;

  if (preview?.segmentId !== segment.id) {
    return points;
  }

  const nextPoints = [...points];
  nextPoints[preview.endpoint === 'start' ? 0 : 1] = preview.previewPoint;
  return nextPoints;
};

const updateSegmentOverlayItems = () => {
  if (!chart || !kSeries) {
    overlayItems.value = [];
    return;
  }

  const nextItems: SegmentOverlayItem[] = [];
  for (const segment of props.segmentLines ?? []) {
    const [startPoint, endPoint] = getSegmentDisplayPoints(segment);
    if (!startPoint || !endPoint) {
      continue;
    }

    const x1 = chart.timeScale().timeToCoordinate(startPoint.time as any);
    const x2 = chart.timeScale().timeToCoordinate(endPoint.time as any);
    const y1 = kSeries.priceToCoordinate(startPoint.value);
    const y2 = kSeries.priceToCoordinate(endPoint.value);

    if (x1 === null || x2 === null || y1 === null || y2 === null) {
      continue;
    }

    nextItems.push({
      id: segment.id,
      segment,
      x1: Number(x1),
      y1: Number(y1),
      x2: Number(x2),
      y2: Number(y2),
      isSelected: selectedSegmentId.value === segment.id,
    });
  }

  overlayItems.value = nextItems;
};

const selectSegment = (segmentId: string) => {
  selectedSegmentId.value = segmentId;
  updateSegmentOverlayItems();
};

const clearSelectedSegment = () => {
  selectedSegmentId.value = null;
  updateSegmentOverlayItems();
};

const closeContextMenu = () => {
  contextMenuState.value = {
    ...contextMenuState.value,
    visible: false,
  };
};

const getDistanceToLineSegment = (
  point: { x: number; y: number },
  lineStart: { x: number; y: number },
  lineEnd: { x: number; y: number },
) => {
  const deltaX = lineEnd.x - lineStart.x;
  const deltaY = lineEnd.y - lineStart.y;
  const lengthSquared = deltaX * deltaX + deltaY * deltaY;

  if (lengthSquared === 0) {
    return Math.hypot(point.x - lineStart.x, point.y - lineStart.y);
  }

  const projection = Math.max(
    0,
    Math.min(1, ((point.x - lineStart.x) * deltaX + (point.y - lineStart.y) * deltaY) / lengthSquared),
  );
  const projectedX = lineStart.x + projection * deltaX;
  const projectedY = lineStart.y + projection * deltaY;

  return Math.hypot(point.x - projectedX, point.y - projectedY);
};

const handleChartClick = (param: any) => {
  closeContextMenu();

  if (dragState.value) {
    return;
  }

  if (!param?.point) {
    clearSelectedSegment();
    return;
  }

  const clickPoint = {
    x: Number(param.point.x),
    y: Number(param.point.y),
  };
  const nearestSegment = overlayItems.value
    .map((item) => ({
      item,
      distance: getDistanceToLineSegment(
        clickPoint,
        { x: item.x1, y: item.y1 },
        { x: item.x2, y: item.y2 },
      ),
    }))
    .sort((first, second) => first.distance - second.distance)[0];

  if (nearestSegment && nearestSegment.distance <= 8) {
    selectSegment(nearestSegment.item.id);
    return;
  }

  clearSelectedSegment();
};

const findNearestKLineInfoByCoordinate = (x: number) => {
  if (!chart) {
    return null;
  }

  let nearestItem: KLineItem | null = null;
  let nearestIndex: number | null = null;
  let nearestDistance = Number.POSITIVE_INFINITY;

  for (let index = 0; index < (props.data.kLineList ?? []).length; index += 1) {
    const item = props.data.kLineList[index];
    if (!item) {
      continue;
    }

    const coordinate = chart.timeScale().timeToCoordinate(item.time as any);
    if (coordinate === null) {
      continue;
    }

    const distance = Math.abs(Number(coordinate) - x);
    if (distance < nearestDistance) {
      nearestDistance = distance;
      nearestItem = item;
      nearestIndex = index;
    }
  }

  if (!nearestItem || nearestIndex === null) {
    return null;
  }

  return {
    item: nearestItem,
    index: nearestIndex,
  };
};

const findNearestKLineByCoordinate = (x: number) => {
  return findNearestKLineInfoByCoordinate(x)?.item ?? null;
};

const getNearestPriceOnKLine = (item: KLineItem, y: number) => {
  const price = kSeries?.coordinateToPrice(y);
  const candidatePrices = [item.open, item.high, item.low, item.close];

  if (price === null || price === undefined || !Number.isFinite(Number(price))) {
    return item.close;
  }

  return candidatePrices.reduce((nearestPrice: number, currentPrice) => {
    return Math.abs(currentPrice - Number(price)) < Math.abs(nearestPrice - Number(price))
      ? currentPrice
      : nearestPrice;
  }, item.open);
};

const getMousePointInChart = (event: MouseEvent) => {
  if (!chartContainer.value) {
    return null;
  }

  const rect = chartContainer.value.getBoundingClientRect();
  return {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  };
};

const getSnappedSegmentPoint = (event: MouseEvent) => {
  const point = getMousePointInChart(event);
  if (!point) {
    return null;
  }

  const nearestKLine = findNearestKLineByCoordinate(point.x);
  if (!nearestKLine) {
    return null;
  }

  return {
    time: nearestKLine.time,
    value: getNearestPriceOnKLine(nearestKLine, point.y),
  };
};

const handleChartContextMenu = (event: MouseEvent) => {
  event.preventDefault();
  closeContextMenu();

  const point = getMousePointInChart(event);
  if (!point || !chartContainer.value) {
    return;
  }

  const nearestSegment = overlayItems.value
    .map((item) => ({
      item,
      distance: getDistanceToLineSegment(
        point,
        { x: item.x1, y: item.y1 },
        { x: item.x2, y: item.y2 },
      ),
    }))
    .sort((first, second) => first.distance - second.distance)[0];

  if (nearestSegment && nearestSegment.distance <= 8) {
    selectSegment(nearestSegment.item.id);
  }

  const nearestKLine = findNearestKLineInfoByCoordinate(point.x);
  contextMenuState.value = {
    visible: true,
    x: point.x,
    y: point.y,
    startIndex: nearestKLine?.index ?? null,
  };
};

const handleCreateSegmentFromContext = () => {
  const startIndex = contextMenuState.value.startIndex;
  if (startIndex === null) {
    return;
  }

  const startItem = props.data.kLineList[startIndex];
  const endItem = props.data.kLineList[startIndex + 5];
  if (!startItem || !endItem) {
    return;
  }

  closeContextMenu();
  emit('segment-line-create', {
    startPoint: {
      time: startItem.time,
      value: startItem.close,
    },
    endPoint: {
      time: endItem.time,
      value: endItem.close,
    },
  });
};

const handleDeleteSegmentFromContext = () => {
  const segment = selectedSegment.value;
  if (!segment || segment.segmentRole !== 'confirmed') {
    return;
  }

  closeContextMenu();
  emit('segment-line-delete', {
    segment,
  });
};

const setChartDragEnabled = (enabled: boolean) => {
  if (!chart) {
    return;
  }

  if (!enabled) {
    const currentOptions = chart.options();
    chartOptionsBeforeDrag = {
      handleScroll: currentOptions.handleScroll,
      handleScale: currentOptions.handleScale,
    };
    chart.applyOptions({
      handleScroll: false,
      handleScale: false,
    });
    return;
  }

  if (chartOptionsBeforeDrag) {
    chart.applyOptions(chartOptionsBeforeDrag);
    chartOptionsBeforeDrag = null;
  }

  chart.applyOptions({
    handleScroll: true,
    handleScale: true,
  });
};

const cleanupEndpointDrag = () => {
  dragState.value = null;
  setChartDragEnabled(true);
  window.removeEventListener('mousemove', handleEndpointMouseMove);
  window.removeEventListener('mouseup', handleEndpointMouseUp);
  updateSegmentOverlayItems();
};

const handleEndpointMouseDown = (
  event: MouseEvent,
  segmentId: string,
  endpoint: 'start' | 'end',
) => {
  event.preventDefault();
  event.stopPropagation();
  selectSegment(segmentId);

  const previewPoint = getSnappedSegmentPoint(event);
  if (!previewPoint) {
    return;
  }

  dragState.value = {
    segmentId,
    endpoint,
    previewPoint,
  };
  setChartDragEnabled(false);
  window.addEventListener('mousemove', handleEndpointMouseMove);
  window.addEventListener('mouseup', handleEndpointMouseUp);
};

const handleEndpointMouseMove = (event: MouseEvent) => {
  if (!dragState.value) {
    return;
  }

  const previewPoint = getSnappedSegmentPoint(event);
  if (!previewPoint) {
    return;
  }

  dragState.value = {
    ...dragState.value,
    previewPoint,
  };
  updateSegmentOverlayItems();
};

const handleEndpointMouseUp = (event: MouseEvent) => {
  if (!dragState.value) {
    return;
  }

  const currentDragState = dragState.value;
  const finalPoint = getSnappedSegmentPoint(event) ?? dragState.value.previewPoint;
  const segment = props.segmentLines.find((item) => item.id === currentDragState.segmentId);
  let changePayload: SegmentLineChange | null = null;

  if (segment) {
    const points = segment.points.map((point) => ({
      time: Number(point.time),
      value: Number(point.value ?? 0),
    }));
    points[currentDragState.endpoint === 'start' ? 0 : 1] = finalPoint;
    points.sort((first, second) => first.time - second.time);

    changePayload = {
      segment,
      endpoint: currentDragState.endpoint,
      points,
    };
  }

  cleanupEndpointDrag();

  if (changePayload) {
    emit('segment-line-change', changePayload);
  }
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
  chartContainer.value.addEventListener('contextmenu', handleChartContextMenu);
  window.addEventListener('click', closeContextMenu);
  window.addEventListener('keydown', closeContextMenu);

  crosshairMoveHandler = (param) => {
    emit('crosshair-move', getCrosshairKLine(param));
  };
  chart.subscribeCrosshairMove(crosshairMoveHandler);
  clickHandler = handleChartClick;
  chart.subscribeClick(clickHandler);
  logicalRangeChangeHandler = () => updateSegmentOverlayItems();
  timeScaleSizeChangeHandler = () => updateSegmentOverlayItems();
  chart.timeScale().subscribeVisibleLogicalRangeChange(logicalRangeChangeHandler);
  chart.timeScale().subscribeSizeChange(timeScaleSizeChangeHandler);

  if (props.autosize) {
    window.addEventListener("resize", resizeHandler);
  }
});

onUnmounted(() => {
  cleanupEndpointDrag();
  if (chartContainer.value) {
    chartContainer.value.removeEventListener('contextmenu', handleChartContextMenu);
  }
  window.removeEventListener('click', closeContextMenu);
  window.removeEventListener('keydown', closeContextMenu);
  if (chart && crosshairMoveHandler) {
    chart.unsubscribeCrosshairMove(crosshairMoveHandler);
    crosshairMoveHandler = null;
  }
  if (chart && clickHandler) {
    chart.unsubscribeClick(clickHandler);
    clickHandler = null;
  }
  if (chart && logicalRangeChangeHandler) {
    chart.timeScale().unsubscribeVisibleLogicalRangeChange(logicalRangeChangeHandler);
    logicalRangeChangeHandler = null;
  }
  if (chart && timeScaleSizeChangeHandler) {
    chart.timeScale().unsubscribeSizeChange(timeScaleSizeChangeHandler);
    timeScaleSizeChangeHandler = null;
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
  segmentSeriesList = [];
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
    selectedSegmentId.value = null;
  },
  { deep: true }
);

watch(
  () => props.segmentLines,
  () => {
    applySegmentLines();
    if (!props.segmentLines.some((segment) => segment.id === selectedSegmentId.value)) {
      selectedSegmentId.value = null;
    }
  },
  { deep: true }
);

watch(selectedSegmentId, () => {
  updateSegmentOverlayItems();
});
</script>

<template>
  <div class="lw-chart-wrap">
    <div class="lw-chart" ref="chartContainer"></div>
    <svg
      class="segment-overlay"
      :width="overlaySize.width"
      :height="overlaySize.height"
      :viewBox="`0 0 ${overlaySize.width} ${overlaySize.height}`"
      :style="{ cursor: overlayCursor }"
    >
      <g v-for="item in overlayItems" :key="item.id">
        <line
          class="segment-overlay__line"
          :class="{ 'segment-overlay__line--selected': item.isSelected }"
          :x1="item.x1"
          :y1="item.y1"
          :x2="item.x2"
          :y2="item.y2"
          :stroke-dasharray="item.segment.lineStyle === 'dashed' ? '8 5' : undefined"
        />
      </g>
    </svg>
    <template v-for="item in overlayItems" :key="`handles-${item.id}`">
      <button
        v-if="item.isSelected"
        class="segment-handle"
        type="button"
        :style="{ left: `${item.x1}px`, top: `${item.y1}px` }"
        @mousedown="handleEndpointMouseDown($event, item.id, 'start')"
      />
      <button
        v-if="item.isSelected"
        class="segment-handle"
        type="button"
        :style="{ left: `${item.x2}px`, top: `${item.y2}px` }"
        @mousedown="handleEndpointMouseDown($event, item.id, 'end')"
      />
    </template>
    <KLineChartContextMenu
      :visible="contextMenuState.visible"
      :x="contextMenuState.x"
      :y="contextMenuState.y"
      :can-create="canCreateSegmentFromContext"
      :can-delete="canDeleteSelectedSegment"
      @create="handleCreateSegmentFromContext"
      @delete="handleDeleteSegmentFromContext"
    />
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

.segment-overlay {
  position: absolute;
  inset: 0;
  z-index: 2;
  width: 100%;
  height: 100%;
  pointer-events: none;

  .segment-overlay__line {
    stroke: transparent;
    stroke-width: 2;
    pointer-events: none;
  }

  .segment-overlay__line--selected {
    stroke: #f59e0b;
    stroke-width: 3;
  }

}

.segment-handle {
  position: absolute;
  z-index: 3;
  width: 14px;
  height: 14px;
  padding: 0;
  border: 2px solid #f59e0b;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.2);
  cursor: grab;
  transform: translate(-50%, -50%);
}

.segment-handle:active {
  cursor: grabbing;
}

.ema-legend {
  position: absolute;
  top: 10px;
  left: 12px;
  z-index: 3;
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
