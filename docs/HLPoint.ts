type PineSeriesLike = {
  get: (offset: number) => number
}

type PineContextLike = {
  new_var: (value?: number) => PineSeriesLike
  setMinimumAdditionalDepth?: (depth: number) => void
}

type PineJsLike = {
  Std: {
    close: (context: unknown) => number
    ema: (series: PineSeriesLike, length: number, context: unknown) => number
    high: (context: unknown) => number
    low: (context: unknown) => number
    open: (context: unknown) => number
  }
}

type PivotKind = 1 | -1

type PivotPoint = {
  kind: PivotKind
  barIndex: number
  price: number
  zoneLower: number
  zoneUpper: number
}

type PendingSegmentEnd = {
  colorIndex: number
  offset: number
  price: number
}

type PendingZonePoint = {
  kind: PivotKind
  offset: number
  lower: number
  upper: number
}

type StudyState = {
  barIndex: number
  bodyRanges: number[]
  lastLongPointIndex: number | null
  lastShortPointIndex: number | null
  pendingSegmentEnd: PendingSegmentEnd | null
  pendingZones: PendingZonePoint[]
  pivotPoints: PivotPoint[]
}

const LOCAL_PIVOT_ZIGZAG_INDICATOR_NAME = 'Local Pivot ZigZag'
const DEFAULT_OFFSET_BARS = 3
const EMA20_LENGTH = 20
const STD120_LENGTH = 120
const MACD_FAST_LENGTH = 4
const MACD_SLOW_LENGTH = 20
const MACD_SIGNAL_LENGTH = 20
const MACD_BOUNDARY_LENGTH = 500

const HIGH_COLOR = '#F23645'
const LOW_COLOR = '#4CAF50'
const ENTRY_HIGH_COLOR = '#2962FF'
const ENTRY_LOW_COLOR = '#E040FB'
const EMA20_COLOR = '#6B7280'

const createState = (): StudyState => ({
  barIndex: -1,
  bodyRanges: [],
  lastLongPointIndex: null,
  lastShortPointIndex: null,
  pendingSegmentEnd: null,
  pendingZones: [],
  pivotPoints: [],
})

const isFiniteNumber = (value: unknown): value is number => (
  typeof value === 'number' && Number.isFinite(value)
)

const getStd = (values: number[], length: number) => {
  if (values.length < length) {
    return 0
  }

  const windowValues = values.slice(-length)
  const average = windowValues.reduce((sum, value) => sum + value, 0) / windowValues.length
  const squaredDiffSum = windowValues.reduce((sum, value) => sum + (value - average) ** 2, 0)
  const divisor = windowValues.length - 1
  return divisor > 0 ? Math.sqrt(squaredDiffSum / divisor) : 0
}

const isConfirmedHigh = (
  highSeries: PineSeriesLike,
  ema20Series: PineSeriesLike,
  offsetBars: number,
) => {
  const candidate = highSeries.get(offsetBars)
  const candidateEma20 = ema20Series.get(offsetBars)
  if (!isFiniteNumber(candidate) || !isFiniteNumber(candidateEma20) || candidate <= candidateEma20) {
    return false
  }

  for (let offset = 0; offset <= offsetBars * 2; offset += 1) {
    if (offset === offsetBars) {
      continue
    }
    const comparedValue = highSeries.get(offset)
    if (!isFiniteNumber(comparedValue) || comparedValue > candidate) {
      return false
    }
  }
  return true
}

const isConfirmedLow = (
  lowSeries: PineSeriesLike,
  ema20Series: PineSeriesLike,
  offsetBars: number,
) => {
  const candidate = lowSeries.get(offsetBars)
  const candidateEma20 = ema20Series.get(offsetBars)
  if (!isFiniteNumber(candidate) || !isFiniteNumber(candidateEma20) || candidate >= candidateEma20) {
    return false
  }

  for (let offset = 0; offset <= offsetBars * 2; offset += 1) {
    if (offset === offsetBars) {
      continue
    }
    const comparedValue = lowSeries.get(offset)
    if (!isFiniteNumber(comparedValue) || comparedValue < candidate) {
      return false
    }
  }
  return true
}

const getRecentPivot = (points: PivotPoint[], kind: PivotKind, occurrence: number) => {
  let found = 0
  for (let index = points.length - 1; index >= 0; index -= 1) {
    const point = points[index]
    if (point?.kind !== kind) {
      continue
    }
    found += 1
    if (found === occurrence) {
      return point
    }
  }
  return null
}

const getRecentPivotBefore = (
  points: PivotPoint[],
  kind: PivotKind,
  beforeBarIndex: number | null,
  occurrence: number,
) => {
  if (beforeBarIndex === null) {
    return null
  }

  let found = 0
  for (let index = points.length - 1; index >= 0; index -= 1) {
    const point = points[index]
    if (!point || point.kind !== kind || point.barIndex >= beforeBarIndex) {
      continue
    }
    found += 1
    if (found === occurrence) {
      return point
    }
  }
  return null
}

const isLess = (left: PivotPoint | null, right: PivotPoint | null) => (
  Boolean(left && right && left.zoneUpper < right.zoneLower)
)

const isGreater = (left: PivotPoint | null, right: PivotPoint | null) => (
  Boolean(left && right && left.zoneLower > right.zoneUpper)
)

const isEqual = (left: PivotPoint | null, right: PivotPoint | null) => (
  Boolean(left && right && left.zoneUpper >= right.zoneLower && left.zoneLower <= right.zoneUpper)
)

const isLongStructure = (
  l1: PivotPoint | null,
  l2: PivotPoint | null,
  l3: PivotPoint | null,
  h1: PivotPoint | null,
  h2: PivotPoint | null,
) => (
  (isLess(l1, l2) && isLess(l2, l3) && isLess(h1, h2))
  || (isGreater(l1, l2) && isLess(l2, l3) && isLess(h1, h2))
  || (isEqual(l1, l2) && isLess(l2, l3) && isLess(h1, h2))
  || (isLess(l1, l2) && isEqual(l2, l3) && isLess(h1, h2))
  || (isLess(l1, l2) && isLess(l2, l3) && isEqual(h1, h2))
  || (isEqual(l1, l2) && isLess(l2, l3) && isEqual(h1, h2))
)

const isShortStructure = (
  h1: PivotPoint | null,
  h2: PivotPoint | null,
  h3: PivotPoint | null,
  l1: PivotPoint | null,
  l2: PivotPoint | null,
) => (
  (isGreater(h1, h2) && isGreater(h2, h3) && isGreater(l1, l2))
  || (isLess(h1, h2) && isGreater(h2, h3) && isGreater(l1, l2))
  || (isEqual(h1, h2) && isGreater(h2, h3) && isGreater(l1, l2))
  || (isGreater(h1, h2) && isEqual(h2, h3) && isGreater(l1, l2))
  || (isGreater(h1, h2) && isGreater(h2, h3) && isEqual(l1, l2))
  || (isEqual(h1, h2) && isGreater(h2, h3) && isEqual(l1, l2))
)

const processPivot = (
  state: StudyState,
  kind: PivotKind,
  barIndex: number,
  price: number,
  center: number,
  tolerance: number,
  requiredDistance: number,
) => {
  const lastPoint = state.pivotPoints[state.pivotPoints.length - 1]
  const point = {
    kind,
    barIndex,
    price,
    zoneLower: center - tolerance,
    zoneUpper: center + tolerance,
  }

  if (!lastPoint) {
    state.pivotPoints.push(point)
    return { added: point, previous: null, replaced: false }
  }

  if (lastPoint.kind === kind) {
    const isMoreExtreme = kind === 1 ? price > lastPoint.price : price < lastPoint.price
    if (isMoreExtreme) {
      Object.assign(lastPoint, point)
      return { added: null, previous: null, replaced: true }
    }
    return { added: null, previous: null, replaced: false }
  }

  const previousPoint = state.pivotPoints[state.pivotPoints.length - 2]
  const isPreviousDownSegmentBroken = (
    kind === 1
    && lastPoint.kind === -1
    && previousPoint?.kind === 1
    && price > previousPoint.price
  )
  if (isPreviousDownSegmentBroken) {
    state.pivotPoints.push(point)
    return { added: point, previous: lastPoint, replaced: false }
  }

  if (barIndex - lastPoint.barIndex > requiredDistance) {
    state.pivotPoints.push(point)
    return { added: point, previous: lastPoint, replaced: false }
  }

  return { added: null, previous: null, replaced: false }
}

const getLocalPivotZigZagIndicatorName = () => LOCAL_PIVOT_ZIGZAG_INDICATOR_NAME

const getCustomIndicators = (PineJS: PineJsLike) => Promise.resolve([
  {
    name: LOCAL_PIVOT_ZIGZAG_INDICATOR_NAME,
    metainfo: {
      _metainfoVersion: 53,
      id: `${LOCAL_PIVOT_ZIGZAG_INDICATOR_NAME}@tv-basicstudies-1`,
      description: LOCAL_PIVOT_ZIGZAG_INDICATOR_NAME,
      shortDescription: 'Pivot ZigZag',
      isCustomIndicator: true,
      is_price_study: true,
      linkedToSeries: true,
      format: {
        type: 'price',
        precision: 2,
      },
      classId: 'ScriptWithDataOffset',
      plots: [
        { id: 'ema20', type: 'line' },
        { id: 'segment', type: 'line' },
        { id: 'segmentOffset', target: 'segment', type: 'dataoffset' },
        { id: 'segmentColor', palette: 'segmentPalette', target: 'segment', type: 'colorer' },
        { id: 'highPoint', type: 'shapes' },
        { id: 'highPointOffset', target: 'highPoint', type: 'dataoffset' },
        { id: 'lowPoint', type: 'shapes' },
        { id: 'lowPointOffset', target: 'lowPoint', type: 'dataoffset' },
        { id: 'longEntry', type: 'shapes' },
        { id: 'longEntryOffset', target: 'longEntry', type: 'dataoffset' },
        { id: 'shortEntry', type: 'shapes' },
        { id: 'shortEntryOffset', target: 'shortEntry', type: 'dataoffset' },
        { id: 'highZoneUpper', type: 'line' },
        { id: 'highZoneUpperOffset', target: 'highZoneUpper', type: 'dataoffset' },
        { id: 'highZoneLower', type: 'line' },
        { id: 'highZoneLowerOffset', target: 'highZoneLower', type: 'dataoffset' },
        { id: 'lowZoneUpper', type: 'line' },
        { id: 'lowZoneUpperOffset', target: 'lowZoneUpper', type: 'dataoffset' },
        { id: 'lowZoneLower', type: 'line' },
        { id: 'lowZoneLowerOffset', target: 'lowZoneLower', type: 'dataoffset' },
      ],
      filledAreas: [
        {
          id: 'highPivotZone',
          objAId: 'highZoneUpper',
          objBId: 'highZoneLower',
          title: 'High PivotZone',
          type: 'plot_plot',
          isHidden: false,
          fillgaps: false,
        },
        {
          id: 'lowPivotZone',
          objAId: 'lowZoneUpper',
          objBId: 'lowZoneLower',
          title: 'Low PivotZone',
          type: 'plot_plot',
          isHidden: false,
          fillgaps: false,
        },
      ],
      styles: {
        ema20: { title: 'EMA20' },
        highPoint: {
          title: 'High Point',
          text: 'H',
          size: 'small',
        },
        highZoneLower: {
          title: 'High Zone Lower',
        },
        highZoneUpper: {
          title: 'High Zone Upper',
        },
        longEntry: {
          title: 'Long Entry',
          text: 'L3',
          size: 'small',
        },
        lowPoint: {
          title: 'Low Point',
          text: 'L',
          size: 'small',
        },
        lowZoneLower: {
          title: 'Low Zone Lower',
        },
        lowZoneUpper: {
          title: 'Low Zone Upper',
        },
        segment: {
          title: 'Pivot Segment',
          joinPoints: false,
        },
        shortEntry: {
          title: 'Short Entry',
          text: 'H3',
          size: 'small',
        },
      },
      defaults: {
        filledAreasStyle: {
          highPivotZone: {
            color: HIGH_COLOR,
            fillType: 'color',
            transparency: 85,
            visible: true,
          },
          lowPivotZone: {
            color: LOW_COLOR,
            fillType: 'color',
            transparency: 85,
            visible: true,
          },
        },
        inputs: {
          offsetBars: DEFAULT_OFFSET_BARS,
          showPoints: true,
          showLines: true,
          showZones: true,
        },
        palettes: {
          segmentPalette: {
            colors: {
              0: {
                color: LOW_COLOR,
                style: 0,
                width: 2,
              },
              1: {
                color: HIGH_COLOR,
                style: 0,
                width: 2,
              },
            },
          },
        },
        styles: {
          ema20: {
            color: EMA20_COLOR,
            linestyle: 0,
            linewidth: 1,
            plottype: 0,
            trackPrice: false,
            transparency: 0,
            visible: true,
          },
          highPoint: {
            color: HIGH_COLOR,
            location: 'Absolute',
            plottype: 'shape_label_down',
            textColor: '#FFFFFF',
            transparency: 0,
            visible: true,
          },
          highZoneLower: {
            color: HIGH_COLOR,
            linestyle: 0,
            linewidth: 1,
            plottype: 0,
            trackPrice: false,
            transparency: 100,
            visible: true,
          },
          highZoneUpper: {
            color: HIGH_COLOR,
            linestyle: 0,
            linewidth: 1,
            plottype: 0,
            trackPrice: false,
            transparency: 100,
            visible: true,
          },
          longEntry: {
            color: ENTRY_LOW_COLOR,
            location: 'Absolute',
            plottype: 'shape_label_up',
            textColor: '#FFFFFF',
            transparency: 0,
            visible: true,
          },
          lowPoint: {
            color: LOW_COLOR,
            location: 'Absolute',
            plottype: 'shape_label_up',
            textColor: '#FFFFFF',
            transparency: 0,
            visible: true,
          },
          lowZoneLower: {
            color: LOW_COLOR,
            linestyle: 0,
            linewidth: 1,
            plottype: 0,
            trackPrice: false,
            transparency: 100,
            visible: true,
          },
          lowZoneUpper: {
            color: LOW_COLOR,
            linestyle: 0,
            linewidth: 1,
            plottype: 0,
            trackPrice: false,
            transparency: 100,
            visible: true,
          },
          segment: {
            color: LOW_COLOR,
            linestyle: 0,
            linewidth: 2,
            plottype: 0,
            trackPrice: false,
            transparency: 0,
            visible: true,
          },
          shortEntry: {
            color: ENTRY_HIGH_COLOR,
            location: 'Absolute',
            plottype: 'shape_label_down',
            textColor: '#FFFFFF',
            transparency: 0,
            visible: true,
          },
        },
      },
      inputs: [
        {
          id: 'offsetBars',
          name: 'Offset Bars',
          defval: DEFAULT_OFFSET_BARS,
          type: 'integer',
          min: 1,
          max: 100,
        },
        {
          id: 'showPoints',
          name: 'Show H/L',
          defval: true,
          type: 'bool',
        },
        {
          id: 'showLines',
          name: 'Show Lines',
          defval: true,
          type: 'bool',
        },
        {
          id: 'showZones',
          name: 'Show PivotZone',
          defval: true,
          type: 'bool',
        },
      ],
      palettes: {
        segmentPalette: {
          colors: {
            0: { name: 'Up Segment' },
            1: { name: 'Down Segment' },
          },
          valToIndex: {
            0: 0,
            1: 1,
          },
        },
      },
    },
    constructor: function (this: {
      _state?: StudyState
      init?: (context: PineContextLike, input: (index: number) => number | boolean) => void
      main?: (context: PineContextLike, input: (index: number) => number | boolean) => number[]
    }) {
      this.init = function () {
        this._state = createState()
      }

      this.main = function (context, input) {
        if (!this._state) {
          this._state = createState()
        }

        const state = this._state
        const offsetBars = Math.max(1, Math.trunc(Number(input(0)) || DEFAULT_OFFSET_BARS))
        const showPoints = input(1) !== false
        const showLines = input(2) !== false
        const showZones = input(3) !== false
        context.setMinimumAdditionalDepth?.(MACD_BOUNDARY_LENGTH + STD120_LENGTH + offsetBars * 2 + 10)

        state.barIndex += 1

        const open = PineJS.Std.open(context)
        const high = PineJS.Std.high(context)
        const low = PineJS.Std.low(context)
        const close = PineJS.Std.close(context)
        const closeSeries = context.new_var(close)
        const ema20 = PineJS.Std.ema(closeSeries, EMA20_LENGTH, context)
        const ema20Series = context.new_var(ema20)
        const fastEma = PineJS.Std.ema(closeSeries, MACD_FAST_LENGTH, context)
        const slowEma = PineJS.Std.ema(closeSeries, MACD_SLOW_LENGTH, context)
        const diff = fastEma - slowEma
        const diffSeries = context.new_var(diff)
        const dea = PineJS.Std.ema(diffSeries, MACD_SIGNAL_LENGTH, context)
        const macd = (diff - dea) * 2
        const macdSeries = context.new_var(macd)
        const absMacdSeries = context.new_var(Math.abs(macd))
        const boundary = PineJS.Std.ema(absMacdSeries, MACD_BOUNDARY_LENGTH, context)
        const highSeries = context.new_var(high)
        const lowSeries = context.new_var(low)
        const openSeries = context.new_var(open)
        const closeValueSeries = context.new_var(close)

        const output = [
          ema20,
          Number.NaN,
          0,
          0,
          Number.NaN,
          0,
          Number.NaN,
          0,
          Number.NaN,
          0,
          Number.NaN,
          0,
          Number.NaN,
          0,
          Number.NaN,
          0,
          Number.NaN,
          0,
          Number.NaN,
          0,
        ]

        if (state.pendingSegmentEnd) {
          output[1] = state.pendingSegmentEnd.price
          output[2] = state.pendingSegmentEnd.offset
          output[3] = state.pendingSegmentEnd.colorIndex
          state.pendingSegmentEnd = null
        }

        const pendingZone = state.pendingZones.shift()
        if (pendingZone) {
          if (pendingZone.kind === 1) {
            output[12] = pendingZone.upper
            output[13] = pendingZone.offset
            output[14] = pendingZone.lower
            output[15] = pendingZone.offset
          } else {
            output[16] = pendingZone.upper
            output[17] = pendingZone.offset
            output[18] = pendingZone.lower
            output[19] = pendingZone.offset
          }
        }

        if ([open, high, low, close].every(isFiniteNumber)) {
          state.bodyRanges.push(Math.abs(close - open))
        }

        const hasEnoughFutureWindow = state.barIndex >= offsetBars * 2
        if (!hasEnoughFutureWindow) {
          return output
        }

        const pivotIndex = state.barIndex - offsetBars
        const pivotHigh = highSeries.get(offsetBars)
        const pivotLow = lowSeries.get(offsetBars)
        const pivotOpen = openSeries.get(offsetBars)
        const pivotClose = closeValueSeries.get(offsetBars)
        const pivotTolerance = getStd(state.bodyRanges.slice(0, Math.max(0, pivotIndex + 1)), STD120_LENGTH)
        const highSignal = isConfirmedHigh(highSeries, ema20Series, offsetBars)
        const lowSignal = isConfirmedLow(lowSeries, ema20Series, offsetBars)
        const macdPrevious = macdSeries.get(1)
        const macdPrevious2 = macdSeries.get(2)
        const insideBoundary = Math.abs(macd) < Math.abs(boundary)
        const longSignal = (
          ((macd <= 0 && macdPrevious < macd && macdPrevious2 < macdPrevious && close > ema20) && insideBoundary)
          || (macd >= 0 && macdPrevious < macd && macdPrevious2 < macdPrevious && close > ema20)
        )
        const shortSignal = (
          ((macd >= 0 && macdPrevious > macd && macdPrevious2 > macdPrevious && close < ema20) && insideBoundary)
          || (macd <= 0 && macdPrevious > macd && macdPrevious2 > macdPrevious && close < ema20)
        )

        const emitPivot = (kind: PivotKind, price: number, center: number) => {
          const result = processPivot(state, kind, pivotIndex, price, center, pivotTolerance, offsetBars)
          if (result.added && showPoints) {
            if (kind === 1) {
              output[4] = price
              output[5] = -offsetBars
            } else {
              output[6] = price
              output[7] = -offsetBars
            }
          }

          if (result.added && result.previous && showLines) {
            const colorIndex = kind === 1 ? 0 : 1
            output[1] = result.previous.price
            output[2] = result.previous.barIndex - state.barIndex
            output[3] = colorIndex
            state.pendingSegmentEnd = {
              colorIndex,
              offset: result.added.barIndex - (state.barIndex + 1),
              price: result.added.price,
            }
          }

          return result
        }

        if (highSignal) {
          const center = Math.max(pivotOpen, pivotClose)
          emitPivot(1, pivotHigh, center)
          if (showZones) {
            const upper = center + pivotTolerance
            const lower = center - pivotTolerance
            state.pendingZones.push(
              { kind: 1, lower, offset: -offsetBars - 3, upper },
              { kind: 1, lower, offset: -offsetBars - 3, upper },
              { kind: 1, lower, offset: -offsetBars - 3, upper },
            )
          }
        }

        if (lowSignal) {
          const center = Math.min(pivotOpen, pivotClose)
          emitPivot(-1, pivotLow, center)
          if (showZones) {
            const upper = center + pivotTolerance
            const lower = center - pivotTolerance
            state.pendingZones.push(
              { kind: -1, lower, offset: -offsetBars - 3, upper },
              { kind: -1, lower, offset: -offsetBars - 3, upper },
              { kind: -1, lower, offset: -offsetBars - 3, upper },
            )
          }
        }

        const longH2 = getRecentPivot(state.pivotPoints, 1, 1)
        const longH1 = getRecentPivotBefore(state.pivotPoints, 1, longH2?.barIndex ?? null, 1)
        const longL2 = getRecentPivotBefore(state.pivotPoints, -1, longH2?.barIndex ?? null, 1)
        const longL1 = getRecentPivotBefore(state.pivotPoints, -1, longL2?.barIndex ?? null, 1)
        const longL3 = lowSignal
          ? state.pivotPoints[state.pivotPoints.length - 1] ?? null
          : null

        const shortL2 = getRecentPivot(state.pivotPoints, -1, 1)
        const shortL1 = getRecentPivotBefore(state.pivotPoints, -1, shortL2?.barIndex ?? null, 1)
        const shortH2 = getRecentPivotBefore(state.pivotPoints, 1, shortL2?.barIndex ?? null, 1)
        const shortH1 = getRecentPivotBefore(state.pivotPoints, 1, shortH2?.barIndex ?? null, 1)
        const shortH3 = highSignal
          ? state.pivotPoints[state.pivotPoints.length - 1] ?? null
          : null

        if (
          longSignal
          && isLongStructure(longL1, longL2, longL3, longH1, longH2)
          && longL3
          && state.lastLongPointIndex !== longL3.barIndex
        ) {
          state.lastLongPointIndex = longL3.barIndex
          output[8] = longL3.price
          output[9] = longL3.barIndex - state.barIndex
        }

        if (
          shortSignal
          && isShortStructure(shortH1, shortH2, shortH3, shortL1, shortL2)
          && shortH3
          && state.lastShortPointIndex !== shortH3.barIndex
        ) {
          state.lastShortPointIndex = shortH3.barIndex
          output[10] = shortH3.price
          output[11] = shortH3.barIndex - state.barIndex
        }

        return output
      }
    },
  },
])

export const localPivotZigZagStrategy = {
  getCustomIndicators,
  getLocalPivotZigZagIndicatorName,
}
