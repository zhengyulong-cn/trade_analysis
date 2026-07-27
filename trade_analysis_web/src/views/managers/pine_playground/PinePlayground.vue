<script setup lang="ts">
import { Indicator, PineRuntimeError, PineTS } from "pinets"
import { computed, ref } from "vue"

type LocalCandle = {
  openTime: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

const DEFAULT_SOURCE = `
//@version=6
indicator("HLPoint ZigZag", overlay = true, max_labels_count = 500, max_lines_count = 500, max_boxes_count = 500, max_bars_back = 5000)

offsetBars = input.int(3, "Offset Bars", minval = 1)
showPoints = input.bool(true, "Show H/L")
showLines = input.bool(true, "Show Lines")
showZones = input.bool(true, "Show Pivot Zones")
highColor = input.color(color.red, "High / Down Color")
lowColor = input.color(color.green, "Low / Up Color")
lineWidth = input.int(2, "Line Width", minval = 1)

zoneFillHigh = color.new(highColor, 85)
zoneFillLow = color.new(lowColor, 85)
zoneBorderHigh = color.new(highColor, 35)
zoneBorderLow = color.new(lowColor, 35)

ema20 = ta.ema(close, 20)
std120 = ta.stdev(math.abs(close - open), 120, false)

isConfirmedHigh(int offset) =>
    candidate = high[offset]
    result = not na(high[offset * 2]) and candidate > ema20[offset]
    for i = 0 to offset * 2
        if i != offset and high[i] > candidate
            result := false
    result

isConfirmedLow(int offset) =>
    candidate = low[offset]
    result = not na(low[offset * 2]) and candidate < ema20[offset]
    for i = 0 to offset * 2
        if i != offset and low[i] < candidate
            result := false
    result

isLongSignal(float macdValue, float boundaryValue, float emaValue) =>
    greenShrinking = macdValue <= 0 and macdValue[1] < macdValue and macdValue[2] < macdValue[1] and close > emaValue
    redGrowing = macdValue >= 0 and macdValue[1] < macdValue and macdValue[2] < macdValue[1] and close > emaValue
    insideBoundary = math.abs(macdValue) < math.abs(boundaryValue)
    (greenShrinking and insideBoundary) or redGrowing

isShortSignal(float macdValue, float boundaryValue, float emaValue) =>
    redShrinking = macdValue >= 0 and macdValue[1] > macdValue and macdValue[2] > macdValue[1] and close < emaValue
    greenGrowing = macdValue <= 0 and macdValue[1] > macdValue and macdValue[2] > macdValue[1] and close < emaValue
    insideBoundary = math.abs(macdValue) < math.abs(boundaryValue)
    (redShrinking and insideBoundary) or greenGrowing

type PivotZone
    float center
    float upper
    float lower

type PivotPoint
    int kind
    int barIndex
    float price
    float zoneUpper
    float zoneLower
    label marker
    line segment
    box zoneBox

var array<PivotPoint> pivotPoints = array.new<PivotPoint>()

buildZone(int kind, int barIndex, float tolerance) =>
    pivotOffset = bar_index - barIndex
    pivotCenter = kind == 1 ? math.max(open[pivotOffset], close[pivotOffset]) : math.min(open[pivotOffset], close[pivotOffset])
    pivotUpper = kind == 1 ? math.min(high[pivotOffset], pivotCenter + tolerance) : pivotCenter + tolerance
    pivotLower = kind == 1 ? pivotCenter - tolerance : math.max(low[pivotOffset], pivotCenter - tolerance)
    PivotZone.new(pivotCenter, pivotUpper, pivotLower)

createZoneBox(int kind, int barIndex, PivotZone zone) =>
    borderColor = kind == 1 ? zoneBorderHigh : zoneBorderLow
    fillColor = kind == 1 ? zoneFillHigh : zoneFillLow
    box.new(left = math.max(barIndex - 2, 0), top = zone.upper, right = barIndex, bottom = zone.lower, border_color = borderColor, bgcolor = fillColor)

addPivot(array<PivotPoint> points, int kind, int barIndex, float price, float tolerance) =>
    PivotZone zone = buildZone(kind, barIndex, tolerance)
    labelText = kind == 1 ? "H" : "L"
    labelStyle = kind == 1 ? label.style_label_down : label.style_label_up
    pointColor = kind == 1 ? highColor : lowColor
    label marker = showPoints ? label.new(barIndex, price, labelText, style = labelStyle, color = pointColor, textcolor = color.white) : na
    line segment = na
    if showLines and array.size(points) > 0
        previousPoint = array.last(points)
        segmentColor = kind == 1 ? lowColor : highColor
        segment := line.new(previousPoint.barIndex, previousPoint.price, barIndex, price, color = segmentColor, width = lineWidth)
    box zoneBox = showZones ? createZoneBox(kind, barIndex, zone) : na
    array.push(points, PivotPoint.new(kind, barIndex, price, zone.upper, zone.lower, marker, segment, zoneBox))

replaceLastPivot(array<PivotPoint> points, int barIndex, float price, float tolerance) =>
    lastPoint = points.pop()
    PivotZone zone = buildZone(lastPoint.kind, barIndex, tolerance)
    lastPoint.barIndex := barIndex
    lastPoint.price := price
    lastPoint.zoneUpper := zone.upper
    lastPoint.zoneLower := zone.lower
    if not na(lastPoint.segment)
        line.set_xy2(lastPoint.segment, barIndex, price)
    if not na(lastPoint.marker)
        label.set_xy(lastPoint.marker, barIndex, price)
    if not na(lastPoint.zoneBox)
        box.set_lefttop(lastPoint.zoneBox, math.max(barIndex - 2, 0), zone.upper)
        box.set_rightbottom(lastPoint.zoneBox, barIndex, zone.lower)
    array.push(points, lastPoint)

processPivot(array<PivotPoint> points, int kind, int barIndex, float price, int requiredDistance, float tolerance) =>
    if array.size(points) == 0
        addPivot(points, kind, barIndex, price, tolerance)
    else
        lastPoint = array.last(points)
        if lastPoint.kind == kind
            isMoreExtreme = kind == 1 ? price > lastPoint.price : price < lastPoint.price
            if isMoreExtreme
                replaceLastPivot(points, barIndex, price, tolerance)
        else
            PivotPoint previousPoint = array.size(points) >= 2 ? array.get(points, array.size(points) - 2) : na
            isPreviousDownSegmentBroken = kind == 1 and lastPoint.kind == -1 and not na(previousPoint) and previousPoint.kind == 1 and price > previousPoint.price
            isPreviousUpSegmentBroken = kind == -1 and lastPoint.kind == 1 and not na(previousPoint) and previousPoint.kind == -1 and price < previousPoint.price
            if isPreviousDownSegmentBroken or isPreviousUpSegmentBroken
                addPivot(points, kind, barIndex, price, tolerance)
            else if barIndex - lastPoint.barIndex > requiredDistance
                addPivot(points, kind, barIndex, price, tolerance)

getRecentPivot(array<PivotPoint> points, int kind, int occurrence) =>
    PivotPoint result = na
    found = 0
    index = array.size(points) - 1
    while index >= 0 and found < occurrence
        point = array.get(points, index)
        if point.kind == kind
            found += 1
            if found == occurrence
                result := point
        index -= 1
    result

findLowestBelowEma20(int startBarIndex, int minimumDistance) =>
    // 在最近顶 Pivot 到当前 K 线之间，寻找 EMA20 下方的最低价作为潜在 L3。
    float lowestPrice = na
    int lowestBarIndex = na
    if not na(startBarIndex)
        barsToSearch = math.min(bar_index - startBarIndex, 4999)
        barsAgo = barsToSearch - minimumDistance
        while barsAgo >= 0
            candidatePrice = low[barsAgo]
            if candidatePrice < ema20[barsAgo] and (na(lowestPrice) or candidatePrice < lowestPrice)
                lowestPrice := candidatePrice
                lowestBarIndex := bar_index - barsAgo
            barsAgo -= 1
    [lowestPrice, lowestBarIndex]

findHighestAboveEma20(int startBarIndex, int minimumDistance) =>
    // 在最近底 Pivot 到当前 K 线之间，寻找 EMA20 上方的最高价作为潜在 H3。
    float highestPrice = na
    int highestBarIndex = na
    if not na(startBarIndex)
        barsToSearch = math.min(bar_index - startBarIndex, 4999)
        barsAgo = barsToSearch - minimumDistance
        while barsAgo >= 0
            candidatePrice = high[barsAgo]
            if candidatePrice > ema20[barsAgo] and (na(highestPrice) or candidatePrice > highestPrice)
                highestPrice := candidatePrice
                highestBarIndex := bar_index - barsAgo
            barsAgo -= 1
    [highestPrice, highestBarIndex]

isLess(PivotPoint leftPoint, PivotPoint rightPoint) =>
    leftPoint.zoneUpper < rightPoint.zoneLower

isGreater(PivotPoint leftPoint, PivotPoint rightPoint) =>
    leftPoint.zoneUpper > rightPoint.zoneLower

isEqual(PivotPoint leftPoint, PivotPoint rightPoint) =>
    leftPoint.zoneUpper >= rightPoint.zoneLower and leftPoint.zoneLower <= rightPoint.zoneUpper

getLongStructurePattern(
    PivotPoint l1,
    PivotPoint l2,
    PivotPoint l3,
    PivotPoint h1,
    PivotPoint h2
) =>
    bool l1LessL2   = isLess(l1, l2)
    bool l1EqualL2  = isEqual(l1, l2)
    bool l2LessL3   = isLess(l2, l3)
    bool l2EqualL3  = isEqual(l2, l3)
    bool h1LessH2   = isLess(h1, h2)
    bool h1EqualH2  = isEqual(h1, h2)

    string pattern = ""
    // 按顺序检查五种模式，匹配则直接返回对应字符串
    // 模式1: L1<L2<L3 and H1<H2
    if l1LessL2 and l2LessL3 and h1LessH2
        pattern := "L1<L2<L3 & H1<H2"
    // 模式2: L1=L2<L3 and H1<H2
    else if l1EqualL2 and l2LessL3 and h1LessH2
        pattern := "L1=L2<L3 & H1<H2"
    // 模式3: L1<L2=L3 and H1<H2
    else if l1LessL2 and l2EqualL3 and h1LessH2
        pattern := "L1<L2=L3 & H1<H2"
    // 模式4: L1<L2<L3 and H1=H2
    else if l1LessL2 and l2LessL3 and h1EqualH2
        pattern := "L1<L2<L3 & H1=H2"
    // 模式5: L1=L2<L3 and H1=H2
    else if l1EqualL2 and l2LessL3 and h1EqualH2
        pattern := "L1=L2<L3 & H1=H2"
    // 都不匹配则保持空字符串
    pattern  // 返回字符串

getShortStructurePattern(
    PivotPoint h1,
    PivotPoint h2,
    PivotPoint h3,
    PivotPoint l1,
    PivotPoint l2
) =>
    bool h1GreaterH2 = isGreater(h1, h2)
    bool h1EqualH2   = isEqual(h1, h2)
    bool h2GreaterH3 = isGreater(h2, h3)
    bool h2EqualH3   = isEqual(h2, h3)
    bool l1GreaterL2 = isGreater(l1, l2)
    bool l1EqualL2   = isEqual(l1, l2)

    string pattern = ""
    // 模式1: H1>H2>H3 and L1>L2
    if h1GreaterH2 and h2GreaterH3 and l1GreaterL2
        pattern := "H1>H2>H3 & L1>L2"
    // 模式2: H1=H2>H3 and L1>L2
    else if h1EqualH2 and h2GreaterH3 and l1GreaterL2
        pattern := "H1=H2>H3 & L1>L2"
    // 模式3: H1>H2=H3 and L1>L2
    else if h1GreaterH2 and h2EqualH3 and l1GreaterL2
        pattern := "H1>H2=H3 & L1>L2"
    // 模式4: H1>H2>H3 and L1=L2
    else if h1GreaterH2 and h2GreaterH3 and l1EqualL2
        pattern := "H1>H2>H3 & L1=L2"
    // 模式5: H1=H2>H3 and L1=L2
    else if h1EqualH2 and h2GreaterH3 and l1EqualL2
        pattern := "H1=H2>H3 & L1=L2"
    // 都不匹配则保持空字符串
    pattern

highSignal = isConfirmedHigh(offsetBars)
lowSignal = isConfirmedLow(offsetBars)

minimumDistance = offsetBars
pivotIndex = bar_index - offsetBars
highPrice = high[offsetBars]
lowPrice = low[offsetBars]
pivotPointStdev = ta.stdev(math.abs(close - open), 120, false)[offsetBars]

if highSignal
    processPivot(pivotPoints, 1, pivotIndex, highPrice, minimumDistance, pivotPointStdev)

if lowSignal
    processPivot(pivotPoints, -1, pivotIndex, lowPrice, minimumDistance, pivotPointStdev)

diff = ta.ema(close, 4) - ema20
dea = ta.ema(diff, 12)
macd = (diff - dea) * 2
boundary = ta.ema(math.abs(macd), 500)

PivotPoint lastPivot = array.size(pivotPoints) == 0 ? na : array.last(pivotPoints)

PivotPoint prev1High = getRecentPivot(pivotPoints, 1, 1)
PivotPoint prev1Low = getRecentPivot(pivotPoints, -1, 1)
PivotPoint prev2High = getRecentPivot(pivotPoints, 1, 2)
PivotPoint prev2Low = getRecentPivot(pivotPoints, -1, 2)
PivotPoint prev3High = getRecentPivot(pivotPoints, 1, 3)
PivotPoint prev3Low = getRecentPivot(pivotPoints, -1, 3)

longSignal = isLongSignal(macd, boundary, ema20)
shortSignal = isShortSignal(macd, boundary, ema20)
hasLastHighPivot = not na(lastPivot) and lastPivot.kind == 1
hasLastLowPivot = not na(lastPivot) and lastPivot.kind == -1

// 最近为顶且出现 longSignal 时，才需要在当前下跌段内搜索潜在 L3。
longSearchStartBarIndex = hasLastHighPivot and longSignal ? lastPivot.barIndex : na
// 最近为底且出现 shortSignal 时，才需要在当前上涨段内搜索潜在 H3。
shortSearchStartBarIndex = hasLastLowPivot and shortSignal ? lastPivot.barIndex : na

[potentialL3Price, potentialL3Index] = findLowestBelowEma20(longSearchStartBarIndex, minimumDistance)
[potentialH3Price, potentialH3Index] = findHighestAboveEma20(shortSearchStartBarIndex, minimumDistance)

// 潜在点仅用于区域比较，不加入 pivotPoints，因此不会额外绘制 H/L 或 Zone。
potentialL3Tolerance = na(potentialL3Index) ? na : nz(std120[bar_index - potentialL3Index], 0.0)
potentialH3Tolerance = na(potentialH3Index) ? na : nz(std120[bar_index - potentialH3Index], 0.0)
PivotPoint potentialL3 = na
PivotPoint potentialH3 = na
if not na(potentialL3Price)
    PivotZone potentialL3Zone = buildZone(-1, potentialL3Index, potentialL3Tolerance)
    potentialL3 := PivotPoint.new(-1, potentialL3Index, potentialL3Price, potentialL3Zone.upper, potentialL3Zone.lower, na, na, na)
if not na(potentialH3Price)
    PivotZone potentialH3Zone = buildZone(1, potentialH3Index, potentialH3Tolerance)
    potentialH3 := PivotPoint.new(1, potentialH3Index, potentialH3Price, potentialH3Zone.upper, potentialH3Zone.lower, na, na, na)

hasLongStructureWithL3 = not na(potentialL3) and not na(prev1Low) and not na(prev2Low) and not na(prev1High) and not na(prev2High)
hasShortStructureWithH3 = not na(potentialH3) and not na(prev1High) and not na(prev2High) and not na(prev1Low) and not na(prev2Low)
hasLongStructureInputs = not na(prev3Low) and not na(prev2Low) and not na(prev1Low) and not na(prev2High) and not na(prev1High)
hasShortStructureInputs = not na(prev3High) and not na(prev2High) and not na(prev1High) and not na(prev2Low) and not na(prev1Low)

string longPatternWithL3 = hasLongStructureWithL3 ? getLongStructurePattern(prev2Low, prev1Low, potentialL3, prev2High, prev1High) : ""
string shortPatternWithH3 = hasShortStructureWithH3 ? getShortStructurePattern(prev2High, prev1High, potentialH3, prev2Low, prev1Low) : ""
string longPatternFromPivots = hasLongStructureInputs ? getLongStructurePattern(prev3Low, prev2Low, prev1Low, prev2High, prev1High) : ""
string shortPatternFromPivots = hasShortStructureInputs ? getShortStructurePattern(prev3High, prev2High, prev1High, prev2Low, prev1Low) : ""

// 最近为顶：有 longSignal 时用潜在 L3 做多；有 shortSignal 时根据已有 Pivot 做空结构。
longEntryFromHigh = hasLastHighPivot and longSignal and longPatternWithL3 != ""
shortEntryFromHigh = hasLastHighPivot and shortSignal and shortPatternFromPivots != ""

// 同一个潜在 L3/H3 只标记一次，避免持续出现入场机会时在同一位置叠加标签。
var int lastMarkedL3Index = na
var int lastMarkedH3Index = na

if longEntryFromHigh
    if na(lastMarkedL3Index) or potentialL3Index != lastMarkedL3Index
        lastMarkedL3Index := potentialL3Index
        label.new(potentialL3Index, potentialL3Price, "L3", style = label.style_label_up, color = color.fuchsia, textcolor = color.white)
    label.new(bar_index, low, longPatternWithL3, style = label.style_label_up, color = color.fuchsia, textcolor = color.white)

if shortEntryFromHigh
    label.new(bar_index, low, shortPatternFromPivots, style = label.style_label_down, color = color.blue, textcolor = color.white)

// 最近为底：有 shortSignal 时用潜在 H3 做空；有 longSignal 时根据已有 Pivot 做多结构。
shortEntryFromLow = hasLastLowPivot and shortSignal and shortPatternWithH3 != ""
longEntryFromLow = hasLastLowPivot and longSignal and longPatternFromPivots != ""

if shortEntryFromLow
    log.info("shortEntryFromLow: prev2High=(bar={0}, price={1}), prev1High=(bar={2}, price={3}), potentialH3=(bar={4}, price={5}), prev2Low=(bar={6}, price={7}), prev1Low=(bar={8}, price={9})", prev2High.barIndex, prev2High.price, prev1High.barIndex, prev1High.price, potentialH3.barIndex, potentialH3.price, prev2Low.barIndex, prev2Low.price, prev1Low.barIndex, prev1Low.price)
    if na(lastMarkedH3Index) or potentialH3Index != lastMarkedH3Index
        lastMarkedH3Index := potentialH3Index
        label.new(potentialH3Index, potentialH3Price, "H3", style = label.style_label_down, color = color.blue, textcolor = color.white)
    label.new(bar_index, high, shortPatternWithH3, style = label.style_label_down, color = color.blue, textcolor = color.white)

if longEntryFromLow
    label.new(bar_index, low, longPatternFromPivots, style = label.style_label_up, color = color.fuchsia, textcolor = color.white)
`

const source = ref(DEFAULT_SOURCE)
const candleCount = ref(1000)
const running = ref(false)
const elapsedMilliseconds = ref<number>()
const result = ref<Record<string, unknown>>()
const errorMessage = ref("")
const debugDetails = ref<Record<string, unknown>>()

const resultText = computed(() => (result.value ? JSON.stringify(result.value, null, 2) : ""))
const debugDetailsText = computed(() =>
  debugDetails.value ? JSON.stringify(debugDetails.value, null, 2) : "",
)

const createCandles = (count: number): LocalCandle[] => {
  const startTime = Date.UTC(2024, 0, 1)
  const candles: LocalCandle[] = []
  let previousClose = 100

  for (let index = 0; index < count; index += 1) {
    const trend = index * 0.015
    const wave = Math.sin(index / 12) * 2.4 + Math.cos(index / 29) * 1.1
    const open = previousClose
    const close = Math.max(1, 100 + trend + wave)
    const range = 0.6 + Math.abs(Math.sin(index / 5)) * 1.8

    candles.push({
      openTime: startTime + index * 60 * 60 * 1000,
      open,
      high: Math.max(open, close) + range,
      low: Math.min(open, close) - range,
      close,
      volume: 1000 + (index % 80) * 35,
    })
    previousClose = close
  }

  return candles
}

const runScript = async () => {
  running.value = true
  result.value = undefined
  errorMessage.value = ""
  elapsedMilliseconds.value = undefined
  debugDetails.value = undefined
  const startedAt = performance.now()
  const candles = createCandles(candleCount.value)

  try {
    console.groupCollapsed("[PineTS Playground] Execute script")
    console.debug("Source", source.value)
    console.debug("Candles", candles)

    const indicator = new Indicator(source.value)
    const prepared = indicator.prepare({ debug: false, ln: false })
    const transpiledCode = prepared.fn.toString()
    debugDetails.value = {
      sourceLength: source.value.length,
      barCount: candles.length,
      firstCandle: candles[0],
      lastCandle: candles.at(-1),
      inputs: prepared.inputs,
      usesVisibleRange: prepared.usesVisibleRange,
      transpilerDebugEnabled: false,
      transpiledCode,
    }
    console.debug("Prepared inputs", prepared.inputs)
    console.debug("Transpiled code", transpiledCode)

    const pine = new PineTS(candles)
    pine.setDebugSettings({ debug: false, ln: false })
    const context = await pine.run(indicator)
    result.value = {
      indicator: context.indicator,
      plots: context.plots,
      warnings: context.warnings,
    }
    console.info("Execution result", result.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "PineTS execution failed."
    const runtimeError = error instanceof PineRuntimeError ? error : undefined
    debugDetails.value = {
      ...debugDetails.value,
      error: {
        name: error instanceof Error ? error.name : typeof error,
        message: errorMessage.value,
        method: runtimeError?.method,
        stack: error instanceof Error ? error.stack : undefined,
      },
    }
    console.error("[PineTS Playground] Execution failed", error)
  } finally {
    elapsedMilliseconds.value = Math.round(performance.now() - startedAt)
    running.value = false
    console.groupEnd()
  }
}

const restoreSample = () => {
  source.value = DEFAULT_SOURCE
  result.value = undefined
  errorMessage.value = ""
  elapsedMilliseconds.value = undefined
  debugDetails.value = undefined
}
</script>

<template>
  <main class="pine-playground">
    <header class="page-toolbar">
      <div>
        <h1>PineTS Playground</h1>
        <p>Local browser execution</p>
      </div>
      <div class="toolbar-actions">
        <el-input-number v-model="candleCount" :min="10" :max="2000" :step="100" controls-position="right" />
        <el-button @click="restoreSample">Restore Sample</el-button>
        <el-button type="primary" :loading="running" @click="runScript">Run Script</el-button>
      </div>
    </header>

    <section class="workspace">
      <section class="editor-pane">
        <el-input v-model="source" type="textarea" :rows="28" resize="none" spellcheck="false" />
      </section>
      <section class="result-pane">
        <div class="result-meta">
          <span>{{ candleCount }} bars</span>
          <span v-if="elapsedMilliseconds !== undefined">{{ elapsedMilliseconds }} ms</span>
        </div>
        <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" show-icon />
        <pre v-else-if="resultText" class="result-output">{{ resultText }}</pre>
        <el-empty v-else description="Run a script to inspect its output." />
        <el-collapse v-if="debugDetailsText" class="debug-details">
          <el-collapse-item title="Debug details">
            <pre class="debug-output">{{ debugDetailsText }}</pre>
          </el-collapse-item>
        </el-collapse>
      </section>
    </section>
  </main>
</template>

<style scoped lang="less">
.pine-playground {
  min-height: calc(100vh - 4rem);
  padding: 20px;
  background: #f5f7fa;
}

.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

h1,
p {
  margin: 0;
}

h1 {
  color: #1f2937;
  font-size: 20px;
  line-height: 1.4;
}

p {
  margin-top: 4px;
  color: #667085;
  font-size: 13px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  min-height: 650px;
  border: 1px solid #dfe5ef;
  border-radius: 6px;
  overflow: hidden;
  background: #ffffff;
}

.editor-pane,
.result-pane {
  min-width: 0;
  padding: 16px;
}

.editor-pane {
  border-right: 1px solid #dfe5ef;
}

.result-pane {
  display: flex;
  flex-direction: column;
}

.result-meta {
  display: flex;
  gap: 12px;
  min-height: 22px;
  margin-bottom: 12px;
  color: #667085;
  font-size: 13px;
}

.result-output {
  flex: 1;
  min-height: 0;
  margin: 0;
  padding: 12px;
  overflow: auto;
  border: 1px solid #dfe5ef;
  border-radius: 4px;
  background: #f8fafc;
  color: #1f2937;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.debug-details {
  margin-top: 12px;
}

.debug-output {
  max-height: 320px;
  margin: 0;
  padding: 12px;
  overflow: auto;
  background: #111827;
  color: #d1d5db;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 900px) {
  .pine-playground {
    padding: 12px;
  }

  .page-toolbar,
  .toolbar-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .workspace {
    grid-template-columns: 1fr;
  }

  .editor-pane {
    border-right: 0;
    border-bottom: 1px solid #dfe5ef;
  }
}
</style>
