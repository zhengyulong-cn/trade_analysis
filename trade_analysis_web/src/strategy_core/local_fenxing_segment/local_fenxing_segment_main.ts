import {
  advanceFenxingState,
  createEmptyFenxingBuildState,
  getAllFenxingSignals,
  getOffsetFromCurrentBar,
  isFiniteNumber,
  truncateFenxingBuildState,
  upsertFenxingBar,
} from './base_fenxing_builder'
import {
  advanceBaseSegmentState,
  createEmptyBaseSegmentBuildState,
  getAllBaseSegments,
  getBaseSegmentKey,
  getLatestDrawableBaseSegment,
  truncateBaseSegmentBuildState,
} from './base_segment_builder'
import {
  advanceHigherLevelSegmentState,
  createEmptyHigherLevelSegmentBuildState,
  getAllHigherLevelSegments,
  getHigherLevelSegmentKey,
  getLatestDrawableHigherLevelSegment,
  truncateHigherLevelSegmentBuildState,
} from './higher_level_segment_builder'
import {
  buildMomentumExhaustionSignals,
  getMomentumExhaustionOutput,
} from './momentum_exhaustion'
import type {
  BaseSegmentBuildState,
  FenxingBar,
  FenxingBuildState,
  HigherLevelSegmentBuildState,
  MomentumExhaustionSignal,
  PineContextLike,
  PineJsLike,
} from './types'

const LOCAL_FENXIN_SEGMENT_INDICATOR_NAME = 'Local Fenxing Segment'
const DEFAULT_EMA20_LENGTH = 20
const DEFAULT_EMA120_LENGTH = 120
const DEFAULT_MAX_INCLUDED_RAW_BAR_COUNT = 4
const DEFAULT_MIN_BAR_DISTANCE = 4
const SEGMENT_LINE_WIDTH = 2
const BASE_SEGMENT_COLOR = '#000000'
const HIGHER_LEVEL_SEGMENT_COLOR = '#FF00FF'
const MOMENTUM_EXHAUSTION_UP_COLOR = '#00AA00'
const MOMENTUM_EXHAUSTION_DOWN_COLOR = '#CC0000'

const getLocalFenxinSegmentIndicatorName = () => LOCAL_FENXIN_SEGMENT_INDICATOR_NAME

type LocalFenxingSegmentStudyState = {
  bars: FenxingBar[]
  baseSegmentBuildState: BaseSegmentBuildState
  emittedInitialDrawableSegmentStartKey: string | null
  emittedInitialHigherDrawableSegmentStartKey: string | null
  fenxingBuildState: FenxingBuildState
  higherLevelSegmentBuildState: HigherLevelSegmentBuildState
  lastSettingsKey: string | null
  momentumExhaustionSignals: MomentumExhaustionSignal[]
}

const createStudyState = (): LocalFenxingSegmentStudyState => ({
  bars: [],
  baseSegmentBuildState: createEmptyBaseSegmentBuildState(),
  emittedInitialDrawableSegmentStartKey: null,
  emittedInitialHigherDrawableSegmentStartKey: null,
  fenxingBuildState: createEmptyFenxingBuildState(),
  higherLevelSegmentBuildState: createEmptyHigherLevelSegmentBuildState(),
  lastSettingsKey: null,
  momentumExhaustionSignals: [],
})

const getCustomIndicators = (PineJS: PineJsLike) => Promise.resolve([
  {
    name: LOCAL_FENXIN_SEGMENT_INDICATOR_NAME,
    metainfo: {
      _metainfoVersion: 53,
      id: `${LOCAL_FENXIN_SEGMENT_INDICATOR_NAME}@tv-basicstudies-1`,
      description: LOCAL_FENXIN_SEGMENT_INDICATOR_NAME,
      shortDescription: 'Fenxing Segment',
      isCustomIndicator: true,
      is_price_study: true,
      linkedToSeries: true,
      format: {
        type: 'price',
        precision: 2,
      },
      classId: 'ScriptWithDataOffset',
      plots: [
        { id: 'segment', type: 'line' },
        { id: 'segmentOffset', target: 'segment', type: 'dataoffset' },
        { id: 'segmentColor', palette: 'segmentPalette', target: 'segment', type: 'colorer' },
        { id: 'higherSegment', type: 'line' },
        { id: 'higherSegmentOffset', target: 'higherSegment', type: 'dataoffset' },
        { id: 'higherSegmentColor', palette: 'higherSegmentPalette', target: 'higherSegment', type: 'colorer' },
        { id: 'momentumExhaustionUp', type: 'shapes' },
        { id: 'momentumExhaustionUpOffset', target: 'momentumExhaustionUp', type: 'dataoffset' },
        { id: 'momentumExhaustionDown', type: 'shapes' },
        { id: 'momentumExhaustionDownOffset', target: 'momentumExhaustionDown', type: 'dataoffset' },
      ],
      styles: {
        higherSegment: {
          title: 'Higher Segment',
          histogramBase: 0,
          joinPoints: false,
        },
        momentumExhaustionDown: {
          title: '空头衰竭',
          text: '空衰',
          size: 'small',
        },
        momentumExhaustionUp: {
          title: '多头衰竭',
          text: '多衰',
          size: 'small',
        },
        segment: {
          title: 'Segment',
          histogramBase: 0,
          joinPoints: false,
        },
      },
      defaults: {
        styles: {
          higherSegment: {
            color: HIGHER_LEVEL_SEGMENT_COLOR,
            linestyle: 0,
            linewidth: SEGMENT_LINE_WIDTH,
            plottype: 0,
            trackPrice: false,
            transparency: 0,
            visible: true,
          },
          momentumExhaustionDown: {
            color: MOMENTUM_EXHAUSTION_DOWN_COLOR,
            location: 'Absolute',
            plottype: 'shape_label_up',
            textColor: '#FFFFFF',
            transparency: 0,
            visible: true,
          },
          momentumExhaustionUp: {
            color: MOMENTUM_EXHAUSTION_UP_COLOR,
            location: 'Absolute',
            plottype: 'shape_label_down',
            textColor: '#FFFFFF',
            transparency: 0,
            visible: true,
          },
          segment: {
            color: BASE_SEGMENT_COLOR,
            linestyle: 0,
            linewidth: SEGMENT_LINE_WIDTH,
            plottype: 0,
            trackPrice: false,
            transparency: 0,
            visible: true,
          },
        },
        palettes: {
          higherSegmentPalette: {
            colors: {
              0: {
                color: HIGHER_LEVEL_SEGMENT_COLOR,
                style: 0,
                width: SEGMENT_LINE_WIDTH,
              },
              1: {
                color: HIGHER_LEVEL_SEGMENT_COLOR,
                style: 0,
                width: SEGMENT_LINE_WIDTH,
              },
            },
          },
          segmentPalette: {
            colors: {
              0: {
                color: BASE_SEGMENT_COLOR,
                style: 0,
                width: SEGMENT_LINE_WIDTH,
              },
              1: {
                color: BASE_SEGMENT_COLOR,
                style: 0,
                width: SEGMENT_LINE_WIDTH,
              },
            },
          },
        },
        inputs: {
          maxIncludedRawBarCount: DEFAULT_MAX_INCLUDED_RAW_BAR_COUNT,
          minBarDistance: DEFAULT_MIN_BAR_DISTANCE,
        },
      },
      palettes: {
        higherSegmentPalette: {
          colors: {
            0: { name: 'Higher Up' },
            1: { name: 'Higher Down' },
          },
          valToIndex: {
            0: 0,
            1: 1,
          },
        },
        segmentPalette: {
          colors: {
            0: { name: 'Up' },
            1: { name: 'Down' },
          },
          valToIndex: {
            0: 0,
            1: 1,
          },
        },
      },
      inputs: [
        {
          id: 'maxIncludedRawBarCount',
          name: '最大包含K线数',
          defval: DEFAULT_MAX_INCLUDED_RAW_BAR_COUNT,
          type: 'integer',
          min: 1,
          max: 50,
        },
        {
          id: 'minBarDistance',
          name: '最小线段K线距离',
          defval: DEFAULT_MIN_BAR_DISTANCE,
          type: 'integer',
          min: 1,
          max: 100,
        },
      ],
    },
    constructor: function (this: {
      _state?: LocalFenxingSegmentStudyState
      init?: (context: PineContextLike, input: (index: number) => number) => void
      main?: (context: PineContextLike, input: (index: number) => number) => unknown
    }) {
      this.init = function () {
        this._state = createStudyState()
      }

      this.main = function (context, input) {
        if (!this._state) {
          this._state = createStudyState()
        }

        const maxIncludedRawBarCount = Math.max(1, Number(input(0)) || DEFAULT_MAX_INCLUDED_RAW_BAR_COUNT)
        const minBarDistance = Math.max(1, Number(input(1)) || DEFAULT_MIN_BAR_DISTANCE)
        const settingsKey = `${maxIncludedRawBarCount}:${minBarDistance}`
        const close = PineJS.Std.close(context)
        const closeSeries = context.new_var(close)
        const ema20 = PineJS.Std.ema(closeSeries, DEFAULT_EMA20_LENGTH, context)
        const ema120 = PineJS.Std.ema(closeSeries, DEFAULT_EMA120_LENGTH, context)
        const high = PineJS.Std.high(context)
        const low = PineJS.Std.low(context)
        const open = PineJS.Std.open(context)
        const time = PineJS.Std.time(context)
        const shouldRebuildStates = this._state.lastSettingsKey !== null && this._state.lastSettingsKey !== settingsKey

        if ([close, ema20, ema120, high, low, open, time].every(isFiniteNumber)) {
          const upsertResult = upsertFenxingBar(this._state.bars, {
            close,
            ema20,
            ema120,
            high,
            low,
            open,
            time,
          })

          if (shouldRebuildStates) {
            this._state.fenxingBuildState = createEmptyFenxingBuildState()
            this._state.baseSegmentBuildState = createEmptyBaseSegmentBuildState()
            this._state.higherLevelSegmentBuildState = createEmptyHigherLevelSegmentBuildState()
            this._state.momentumExhaustionSignals = []
            this._state.emittedInitialDrawableSegmentStartKey = null
            this._state.emittedInitialHigherDrawableSegmentStartKey = null
          } else if (upsertResult.type !== 'append') {
            const nextFenxingSignalIndex = truncateFenxingBuildState(this._state.fenxingBuildState, upsertResult.index)
            this._state.emittedInitialDrawableSegmentStartKey = null
            this._state.emittedInitialHigherDrawableSegmentStartKey = null
            truncateBaseSegmentBuildState(
              this._state.baseSegmentBuildState,
              this._state.bars,
              getAllFenxingSignals(this._state.fenxingBuildState),
              nextFenxingSignalIndex,
              minBarDistance,
            )
            truncateHigherLevelSegmentBuildState(
              this._state.higherLevelSegmentBuildState,
              this._state.bars,
              getAllBaseSegments(this._state.baseSegmentBuildState),
              upsertResult.index,
              minBarDistance,
            )
          }

          advanceFenxingState(this._state.fenxingBuildState, this._state.bars, maxIncludedRawBarCount)
          advanceBaseSegmentState(
            this._state.baseSegmentBuildState,
            this._state.bars,
            getAllFenxingSignals(this._state.fenxingBuildState),
            minBarDistance,
          )
          advanceHigherLevelSegmentState(
            this._state.higherLevelSegmentBuildState,
            this._state.bars,
            getAllBaseSegments(this._state.baseSegmentBuildState),
            minBarDistance,
          )
        }

        this._state.lastSettingsKey = settingsKey

        const latestBaseSegment = getLatestDrawableBaseSegment(this._state.baseSegmentBuildState)
        const latestHigherLevelSegment = getLatestDrawableHigherLevelSegment(
          this._state.higherLevelSegmentBuildState,
          minBarDistance,
        )

        const higherLevelSegments = getAllHigherLevelSegments(
          this._state.higherLevelSegmentBuildState,
          minBarDistance,
        )

        this._state.momentumExhaustionSignals = buildMomentumExhaustionSignals(
          this._state.bars,
          getAllBaseSegments(this._state.baseSegmentBuildState),
          higherLevelSegments,
        )

        const baseSegmentOutput = (() => {
          if (!latestBaseSegment) {
            return [Number.NaN, Number.NaN, Number.NaN]
          }

          const baseSegmentColor = latestBaseSegment.direction === 'up' ? 0 : 1
          const latestBaseSegmentKey = getBaseSegmentKey(latestBaseSegment)

          if (this._state.emittedInitialDrawableSegmentStartKey !== latestBaseSegmentKey) {
            this._state.emittedInitialDrawableSegmentStartKey = latestBaseSegmentKey
            return [
              latestBaseSegment.start.price,
              getOffsetFromCurrentBar(this._state.bars, latestBaseSegment.start),
              baseSegmentColor,
            ]
          }

          return [
            latestBaseSegment.end.price,
            getOffsetFromCurrentBar(this._state.bars, latestBaseSegment.end),
            baseSegmentColor,
          ]
        })()

        const higherLevelSegmentOutput = (() => {
          if (!latestHigherLevelSegment) {
            return [Number.NaN, Number.NaN, Number.NaN]
          }

          const higherSegmentColor = latestHigherLevelSegment.direction === 'up' ? 0 : 1
          const latestHigherSegmentKey = getHigherLevelSegmentKey(latestHigherLevelSegment)

          if (this._state.emittedInitialHigherDrawableSegmentStartKey !== latestHigherSegmentKey) {
            this._state.emittedInitialHigherDrawableSegmentStartKey = latestHigherSegmentKey
            return [
              latestHigherLevelSegment.start.price,
              getOffsetFromCurrentBar(this._state.bars, latestHigherLevelSegment.start),
              higherSegmentColor,
            ]
          }

          return [
            latestHigherLevelSegment.end.price,
            getOffsetFromCurrentBar(this._state.bars, latestHigherLevelSegment.end),
            higherSegmentColor,
          ]
        })()

        const momentumExhaustionOutput = getMomentumExhaustionOutput(
          this._state.bars,
          this._state.momentumExhaustionSignals,
        )

        const seriesOutput = [
          ...baseSegmentOutput,
          ...higherLevelSegmentOutput,
          ...momentumExhaustionOutput,
        ]
        return seriesOutput
      }
    },
  },
])

export const localFenxinSegmentStrategy = {
  getCustomIndicators,
  getLocalFenxinSegmentIndicatorName,
}
