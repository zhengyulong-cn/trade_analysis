import {
  advanceBaseSegmentState,
  createEmptyBaseSegmentBuildState,
  getBaseSegmentKey,
  getOffsetFromCurrentBar,
  getLatestDrawableBaseSegment,
  isFiniteNumber,
  rebuildBaseSegmentState,
  upsertBar,
} from './base_segment_builder'
import type { BaseSegmentStudyState, PineContextLike, PineJsLike } from './types'

const LOCAL_EMA_SEGMENT_INDICATOR_NAME = 'Local EMA Segment'
const DEFAULT_EMA_LENGTH = 20
const DEFAULT_MIN_SEGMENT_BARS = 4
const SEGMENT_LINE_WIDTH = 2

const createStudyState = (): BaseSegmentStudyState => ({
  bars: [],
  emittedInitialBaseSegmentStartKey: null,
  lastSettingsKey: null,
  baseSegmentBuildState: createEmptyBaseSegmentBuildState(),
})

const getLocalEmaSegmentIndicatorName = () => LOCAL_EMA_SEGMENT_INDICATOR_NAME

const getCustomIndicators = (PineJS: PineJsLike) => Promise.resolve([
  {
    name: LOCAL_EMA_SEGMENT_INDICATOR_NAME,
    metainfo: {
      _metainfoVersion: 53,
      id: `${LOCAL_EMA_SEGMENT_INDICATOR_NAME}@tv-basicstudies-1`,
      description: LOCAL_EMA_SEGMENT_INDICATOR_NAME,
      shortDescription: 'EMA Segment',
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
          title: 'Segment',
          histogramBase: 0,
          joinPoints: false,
        },
      },
      defaults: {
        styles: {
          segment: {
            color: '#F23645',
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
                color: '#F23645',
                style: 0,
                width: SEGMENT_LINE_WIDTH,
              },
              1: {
                color: '#089981',
                style: 0,
                width: SEGMENT_LINE_WIDTH,
              },
            },
          },
        },
        inputs: {
          emaLength: DEFAULT_EMA_LENGTH,
          minSegmentBars: DEFAULT_MIN_SEGMENT_BARS,
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
          id: 'emaLength',
          name: 'EMA Length',
          defval: DEFAULT_EMA_LENGTH,
          type: 'integer',
          min: 1,
          max: 500,
        },
        {
          id: 'minSegmentBars',
          name: 'Min Segment Bars',
          defval: DEFAULT_MIN_SEGMENT_BARS,
          type: 'integer',
          min: 1,
          max: 500,
        },
      ],
    },
    constructor: function (this: {
      _state?: BaseSegmentStudyState
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

        const emaLength = Math.max(1, Number(input(0)) || DEFAULT_EMA_LENGTH)
        const minSegmentBars = Math.max(1, Number(input(1)) || DEFAULT_MIN_SEGMENT_BARS)
        const settingsKey = `${emaLength}:${minSegmentBars}`
        const close = PineJS.Std.close(context)
        const closeSeries = context.new_var(close)
        const ema = PineJS.Std.ema(closeSeries, emaLength, context)
        const time = PineJS.Std.time(context)
        const high = PineJS.Std.high(context)
        const low = PineJS.Std.low(context)
        let shouldRebuildBaseSegments = this._state.lastSettingsKey !== null && this._state.lastSettingsKey !== settingsKey

        if (isFiniteNumber(time) && isFiniteNumber(close) && isFiniteNumber(high) && isFiniteNumber(low)) {
          const upsertResult = upsertBar(this._state.bars, {
            close,
            ema,
            high,
            low,
            time,
          })

          shouldRebuildBaseSegments = shouldRebuildBaseSegments || upsertResult.type !== 'append'
        }

        this._state.lastSettingsKey = settingsKey

        if (shouldRebuildBaseSegments || this._state.baseSegmentBuildState.processedBarCount > this._state.bars.length) {
          this._state.baseSegmentBuildState = rebuildBaseSegmentState(this._state.bars, emaLength, minSegmentBars)
        } else if (this._state.baseSegmentBuildState.processedBarCount < this._state.bars.length) {
          advanceBaseSegmentState(this._state.baseSegmentBuildState, this._state.bars, emaLength, minSegmentBars)
        }

        const latestBaseSegment = getLatestDrawableBaseSegment(this._state.baseSegmentBuildState)

        if (!latestBaseSegment) {
          return [
            Number.NaN,
            Number.NaN,
            Number.NaN,
          ]
        }
        const baseSegmentColor = latestBaseSegment.direction === 'up' ? 0 : 1
        const latestBaseSegmentKey = getBaseSegmentKey(latestBaseSegment)
        if (this._state.emittedInitialBaseSegmentStartKey !== latestBaseSegmentKey) {
          this._state.emittedInitialBaseSegmentStartKey = latestBaseSegmentKey
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
      }
    },
  },
])

export const localEmaSegmentStrategy = {
  getCustomIndicators,
  getLocalEmaSegmentIndicatorName,
}
