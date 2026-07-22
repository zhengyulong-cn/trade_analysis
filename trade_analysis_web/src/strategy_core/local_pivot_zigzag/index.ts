import { isConfirmedHigh, isConfirmedLow } from "./hl_signals_builder"
import type { PineContextLike, PineJsLike, StudyState } from "./types"

const DEFAULT_OFFSET_BARS = 3
const EMA20_LENGTH = 20
const HIGH_COLOR = '#F23645'
const LOW_COLOR = '#4CAF50'

const LOCAL_PIVOT_ZIGZAG_INDICATOR_NAME = 'Local Pivot ZigZag'

const createState = (): StudyState => ({
  barIndex: -1,
  bodyRanges: [],
  lastLongPointIndex: null,
  lastShortPointIndex: null,
  pendingSegmentEnd: null,
  pendingZones: [],
  pivotPoints: [],
})

const getLocalPivotZigZagIndicatorName = () => LOCAL_PIVOT_ZIGZAG_INDICATOR_NAME

const getCustomIndicators = (PineJS: PineJsLike) => Promise.resolve([
  {
    name: LOCAL_PIVOT_ZIGZAG_INDICATOR_NAME,
    metainfo: {
      _metainfoVersion: 13,
      id: `${LOCAL_PIVOT_ZIGZAG_INDICATOR_NAME}@tv-basicstudies-1`,
      description: LOCAL_PIVOT_ZIGZAG_INDICATOR_NAME,
      shortDescription: 'Pivot ZigZag',
      isCustomIndicator: true,
      is_price_study: true,
      linkedToSeries: true,
      classId: 'ScriptWithDataOffset',
      format: { precision: 2, type: 'price' },
      plots: [
        { id: 'highPoint', type: 'shapes' },
        { id: 'highPointOffset', target: 'highPoint', type: 'dataoffset' },
        { id: 'lowPoint', type: 'shapes' },
        { id: 'lowPointOffset', target: 'lowPoint', type: 'dataoffset' },
      ],
      styles: {
        highPoint: {
          title: 'High Point',
          text: 'H',
          size: 'small',
        },
        lowPoint: {
          title: 'Low Point',
          text: 'L',
          size: 'small',
        },
      },
      defaults: {
        inputs: {
          offsetBars: DEFAULT_OFFSET_BARS,
          showPoints: true,
        },
        styles: {
          highPoint: {
            color: HIGH_COLOR,
            location: 'Absolute',
            plottype: 'shape_label_down',
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
      ],
    },
    constructor: function (this: {
      _state?: StudyState
      init?: (context: PineContextLike) => void
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
        context.setMinimumAdditionalDepth?.(EMA20_LENGTH + offsetBars * 2 + 1)

        state.barIndex += 1

        const close = PineJS.Std.close(context)
        const closeSeries = context.new_var(close)
        const ema20 = PineJS.Std.ema(closeSeries, EMA20_LENGTH, context)
        const ema20Series = context.new_var(ema20)
        const highSeries = context.new_var(PineJS.Std.high(context))
        const lowSeries = context.new_var(PineJS.Std.low(context))

        const highSignal = isConfirmedHigh(highSeries, ema20Series, offsetBars)
        const lowSignal = isConfirmedLow(lowSeries, ema20Series, offsetBars)
        const candidateHigh = highSeries.get(offsetBars)
        const candidateLow = lowSeries.get(offsetBars)

        return [
          // showPoints && highSignal ? candidateHigh * 1.001 : Number.NaN,
          candidateHigh,
          -offsetBars,
          showPoints && lowSignal ? candidateLow * 0.999 : Number.NaN,
          -offsetBars,
        ]
      }
    },
  },
])

export const localPivotZigZagStrategy = {
  getCustomIndicators,
  getLocalPivotZigZagIndicatorName,
}
