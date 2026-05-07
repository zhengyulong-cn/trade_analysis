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
  getBaseSegmentKey,
  getLatestDrawableBaseSegment,
  truncateBaseSegmentBuildState,
} from './base_segment_builder'
import type { BaseSegmentBuildState, FenxingBar, FenxingBuildState } from './types'
import type { PineContextLike, PineJsLike } from './types'

const LOCAL_FENXIN_SEGMENT_INDICATOR_NAME = '分型线段'
const DEFAULT_EMA_LENGTH = 20
// 默认分型包含运算最多K线数量
const DEFAULT_MAX_INCLUDED_RAW_BAR_COUNT = 4
// 默认线段最短K线距离
const DEFAULT_MIN_BAR_DISTANCE = 4
const SEGMENT_LINE_WIDTH = 2

const getLocalFenxinSegmentIndicatorName = () => LOCAL_FENXIN_SEGMENT_INDICATOR_NAME

type LocalFenxingSegmentStudyState = {
  bars: FenxingBar[]
  fenxingBuildState: FenxingBuildState
  baseSegmentBuildState: BaseSegmentBuildState
  emittedInitialDrawableSegmentStartKey: string | null
  lastSettingsKey: string | null
}

const createStudyState = (): LocalFenxingSegmentStudyState => ({
  bars: [],
  baseSegmentBuildState: createEmptyBaseSegmentBuildState(),
  fenxingBuildState: createEmptyFenxingBuildState(),
  emittedInitialDrawableSegmentStartKey: null,
  lastSettingsKey: null,
})

const getCustomIndicators = (PineJS: PineJsLike) => Promise.resolve([
  {
    name: LOCAL_FENXIN_SEGMENT_INDICATOR_NAME,
    metainfo: {
      _metainfoVersion: 53,
      id: `${LOCAL_FENXIN_SEGMENT_INDICATOR_NAME}@tv-basicstudies-1`,
      description: LOCAL_FENXIN_SEGMENT_INDICATOR_NAME,
      shortDescription: 'Fenxing',
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
      ],
      styles: {
        segment: {
          title: 'Fenxing Segment',
          histogramBase: 0,
          joinPoints: false,
        },
      },
      defaults: {
        styles: {
          segment: {
            color: '#000000',
            linestyle: 0,
            linewidth: SEGMENT_LINE_WIDTH,
            plottype: 0,
            trackPrice: false,
            transparency: 0,
            visible: true,
          },
        },
        palettes: {
          segmentPalette: {
            colors: {
              0: {
                color: '#000000',
                style: 0,
                width: SEGMENT_LINE_WIDTH,
              },
              1: {
                color: '#000000',
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
          name: '分型包含运算最多K线数量',
          defval: DEFAULT_MAX_INCLUDED_RAW_BAR_COUNT,
          type: 'integer',
          min: 1,
          max: 50,
        },
        {
          id: 'minBarDistance',
          name: '线段最短K线距离',
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
        const ema20 = PineJS.Std.ema(closeSeries, DEFAULT_EMA_LENGTH, context)
        const high = PineJS.Std.high(context)
        const low = PineJS.Std.low(context)
        const open = PineJS.Std.open(context)
        const time = PineJS.Std.time(context)
        const shouldRebuildStates = this._state.lastSettingsKey !== null && this._state.lastSettingsKey !== settingsKey

        if ([close, ema20, high, low, open, time].every(isFiniteNumber)) {
          const upsertResult = upsertFenxingBar(this._state.bars, {
            close,
            ema20,
            high,
            low,
            open,
            time,
          })

          if (shouldRebuildStates) {
            this._state.fenxingBuildState = createEmptyFenxingBuildState()
            this._state.baseSegmentBuildState = createEmptyBaseSegmentBuildState()
            this._state.emittedInitialDrawableSegmentStartKey = null
          } else if (upsertResult.type !== 'append') {
            const nextFenxingSignalIndex = truncateFenxingBuildState(this._state.fenxingBuildState, upsertResult.index)
            this._state.emittedInitialDrawableSegmentStartKey = null
            truncateBaseSegmentBuildState(
              this._state.baseSegmentBuildState,
              this._state.bars,
              getAllFenxingSignals(this._state.fenxingBuildState),
              nextFenxingSignalIndex,
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
        }

        this._state.lastSettingsKey = settingsKey

        const latestBaseSegment = getLatestDrawableBaseSegment(this._state.baseSegmentBuildState)
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

        return baseSegmentOutput
      }
    },
  },
])

export const localFenxinSegmentStrategy = {
  getCustomIndicators,
  getLocalFenxinSegmentIndicatorName,
}
