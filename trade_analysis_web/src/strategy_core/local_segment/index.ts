import { buildBaseHLPoint, type PineSeriesLike } from './base_HL_point_builder'

type PineContextLike = {
  new_var: (value?: number) => PineSeriesLike
  setMinimumAdditionalDepth: (depth: number) => void
}

type PineJsLike = {
  Std: {
    close: (context: unknown) => number
    ema: (series: PineSeriesLike, length: number, context: unknown) => number
    high: (context: unknown) => number
    low: (context: unknown) => number
  }
}

const LOCAL_SEGMENT_INDICATOR_NAME = '高低点线段'
const DEFAULT_OFFSET_BARS = 3
const DEFAULT_EMA20_LENGTH = 20

const getLocalSegmentIndicatorName = () => LOCAL_SEGMENT_INDICATOR_NAME

const getCustomIndicators = (PineJS: PineJsLike) => Promise.resolve([
  {
    name: LOCAL_SEGMENT_INDICATOR_NAME,
    metainfo: {
      _metainfoVersion: 53,
      id: `${LOCAL_SEGMENT_INDICATOR_NAME}@tv-basicstudies-1`,
      description: LOCAL_SEGMENT_INDICATOR_NAME,
      shortDescription: 'Segment H/L',
      isCustomIndicator: true,
      is_price_study: true,
      linkedToSeries: true,
      format: {
        type: 'price',
        precision: 2,
      },
      classId: 'ScriptWithDataOffset',
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
        styles: {
          highPoint: {
            color: '#F23645',
            location: 'Absolute',
            plottype: 'shape_label_down',
            textColor: '#FFFFFF',
            transparency: 0,
            visible: true,
          },
          lowPoint: {
            color: '#089981',
            location: 'Absolute',
            plottype: 'shape_label_up',
            textColor: '#FFFFFF',
            transparency: 0,
            visible: true,
          },
        },
        inputs: {
          offsetBars: DEFAULT_OFFSET_BARS,
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
      ],
    },
    constructor: function (this: {
      init?: (context: PineContextLike, input: (index: number) => number) => void
      main?: (context: PineContextLike, input: (index: number) => number) => number[]
    }) {
      this.main = function (context, input) {
        const offsetBars = Math.max(1, Math.trunc(Number(input(0)) || DEFAULT_OFFSET_BARS))
        context.setMinimumAdditionalDepth(DEFAULT_EMA20_LENGTH + offsetBars * 2 + 1)

        const close = PineJS.Std.close(context)
        const closeSeries = context.new_var(close)
        const ema20 = PineJS.Std.ema(closeSeries, DEFAULT_EMA20_LENGTH, context)
        const ema20Series = context.new_var(ema20)
        const high = PineJS.Std.high(context)
        const low = PineJS.Std.low(context)
        const highSeries = context.new_var(high)
        const lowSeries = context.new_var(low)
        const { candidateHigh, candidateLow, highPoint, lowPoint } = buildBaseHLPoint(
          highSeries,
          lowSeries,
          ema20Series,
          offsetBars,
        )

        return [
          highPoint ? candidateHigh * 1.001 : Number.NaN,
          -offsetBars,
          lowPoint ? candidateLow * 0.999 : Number.NaN,
          -offsetBars,
        ]
      }
    },
  },
])

export const localSegmentStrategy = {
  getCustomIndicators,
  getLocalSegmentIndicatorName,
}
