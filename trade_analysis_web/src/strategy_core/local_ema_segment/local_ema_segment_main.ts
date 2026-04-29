import {
  buildEmaSegments,
  getOffsetFromCurrentBar,
  getSegmentKey,
  isFiniteNumber,
  upsertBar,
} from './segment_builder'
import {
  buildMomentumExhaustionSignals,
  getMomentumExhaustionOutput,
} from './momentum_exhaustion'
import type { EmaSegmentStudyState, PineContextLike, PineJsLike } from './types'

const LOCAL_EMA_SEGMENT_INDICATOR_NAME = 'Local EMA Segment'
const DEFAULT_EMA_LENGTH = 20
const DEFAULT_MIN_SEGMENT_BARS = 5
const SEGMENT_LINE_WIDTH = 2
const MOMENTUM_EXHAUSTION_COLOR = '#ffcc00'

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
        { id: 'upMomentumExhaustion', type: 'shapes' },
        { id: 'upMomentumExhaustionOffset', target: 'upMomentumExhaustion', type: 'dataoffset' },
        { id: 'downMomentumExhaustion', type: 'shapes' },
        { id: 'downMomentumExhaustionOffset', target: 'downMomentumExhaustion', type: 'dataoffset' },
      ],
      styles: {
        segment: {
          title: 'Segment',
          histogramBase: 0,
          joinPoints: false,
        },
        upMomentumExhaustion: {
          title: '多头衰竭',
          text: '多头衰竭',
          size: 'small',
        },
        downMomentumExhaustion: {
          title: '空头衰竭',
          text: '空头衰竭',
          size: 'small',
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
          upMomentumExhaustion: {
            color: MOMENTUM_EXHAUSTION_COLOR,
            location: 'Absolute',
            plottype: 'shape_label_down',
            textColor: '#000000',
            transparency: 0,
            visible: true,
          },
          downMomentumExhaustion: {
            color: MOMENTUM_EXHAUSTION_COLOR,
            location: 'Absolute',
            plottype: 'shape_label_up',
            textColor: '#000000',
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
      _state?: EmaSegmentStudyState
      init?: (context: PineContextLike, input: (index: number) => number) => void
      main?: (context: PineContextLike, input: (index: number) => number) => unknown
    }) {
      this.init = function () {
        this._state = {
          bars: [],
          emittedInitialStartKey: null,
        }
      }

      this.main = function (context, input) {
        if (!this._state) {
          this._state = {
            bars: [],
            emittedInitialStartKey: null,
          }
        }

        const emaLength = Math.max(1, Number(input(0)) || DEFAULT_EMA_LENGTH)
        const minSegmentBars = Math.max(1, Number(input(1)) || DEFAULT_MIN_SEGMENT_BARS)
        const close = PineJS.Std.close(context)
        const closeSeries = context.new_var(close)
        const ema = PineJS.Std.ema(closeSeries, emaLength, context)
        const time = PineJS.Std.time(context)
        const high = PineJS.Std.high(context)
        const low = PineJS.Std.low(context)

        if (isFiniteNumber(time) && isFiniteNumber(close) && isFiniteNumber(high) && isFiniteNumber(low)) {
          upsertBar(this._state.bars, {
            close,
            ema,
            high,
            low,
            time,
          })
        }

        const segments = buildEmaSegments(this._state.bars, emaLength, minSegmentBars)
        const latestSegment = segments[segments.length - 1]
        const momentumExhaustionOutput = getMomentumExhaustionOutput(
          this._state.bars,
          buildMomentumExhaustionSignals(this._state.bars, segments),
        )

        if (!latestSegment) {
          return [
            Number.NaN,
            Number.NaN,
            Number.NaN,
            ...momentumExhaustionOutput,
          ]
        }

        const segmentColor = latestSegment.direction === 'up' ? 0 : 1
        const latestSegmentKey = getSegmentKey(latestSegment)
        if (this._state.emittedInitialStartKey !== latestSegmentKey) {
          this._state.emittedInitialStartKey = latestSegmentKey
          return [
            latestSegment.start.price,
            getOffsetFromCurrentBar(this._state.bars, latestSegment.start),
            segmentColor,
            ...momentumExhaustionOutput,
          ]
        }

        return [
          latestSegment.end.price,
          getOffsetFromCurrentBar(this._state.bars, latestSegment.end),
          segmentColor,
          ...momentumExhaustionOutput,
        ]
      }
    },
  },
])

export const localEmaSegmentStrategy = {
  getCustomIndicators,
  getLocalEmaSegmentIndicatorName,
}
