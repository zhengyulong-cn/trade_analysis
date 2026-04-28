type PineJsLike = {
  Std: {
    close: (context: unknown) => number
    ema: (source: unknown, length: number, context: unknown) => number
    high: (context: unknown) => number
    low: (context: unknown) => number
    time: (context: unknown) => number
  }
}

type PineContextLike = {
  new_var: (value?: number) => unknown
  symbol?: {
    isLastBar?: boolean
  }
}

type SegmentDirection = 'up' | 'down'

type EmaSegmentBar = {
  close: number
  ema: number
  high: number
  index: number
  low: number
  time: number
}

type SegmentPoint = {
  index: number
  price: number
  time: number
}

type EmaSegment = {
  direction: SegmentDirection
  end: SegmentPoint
  start: SegmentPoint
}

type EmaSegmentStudyState = {
  bars: EmaSegmentBar[]
  emittedInitialStartKey: string | null
}

const LOCAL_EMA_SEGMENT_INDICATOR_NAME = 'Local EMA Segment'
const DEFAULT_EMA_LENGTH = 20
const DEFAULT_MIN_SEGMENT_BARS = 5
const SEGMENT_LINE_WIDTH = 2

const getLocalEmaSegmentIndicatorName = () => LOCAL_EMA_SEGMENT_INDICATOR_NAME

const isFiniteNumber = (value: number) => Number.isFinite(value) && !Number.isNaN(value)

const upsertBar = (bars: EmaSegmentBar[], bar: Omit<EmaSegmentBar, 'index'>) => {
  const lastBar = bars[bars.length - 1]

  if (!lastBar || bar.time > lastBar.time) {
    bars.push({
      ...bar,
      index: bars.length,
    })
    return
  }

  if (bar.time === lastBar.time) {
    bars[bars.length - 1] = {
      ...bar,
      index: lastBar.index,
    }
    return
  }

  const existingIndex = bars.findIndex((item) => item.time === bar.time)
  if (existingIndex >= 0) {
    bars[existingIndex] = {
      ...bar,
      index: existingIndex,
    }
    return
  }

  bars.push({
    ...bar,
    index: bars.length,
  })
  bars.sort((first, second) => first.time - second.time)
  bars.forEach((item, index) => {
    item.index = index
  })
}

const getSegmentExtreme = (bar: EmaSegmentBar, direction: SegmentDirection): SegmentPoint => ({
  index: bar.index,
  price: direction === 'up' ? bar.high : bar.low,
  time: bar.time,
})

const createSegment = (
  direction: SegmentDirection,
  start: SegmentPoint,
  end: SegmentPoint,
): EmaSegment => ({
  direction,
  start: { ...start },
  end: { ...end },
})

const updateLastSegmentEnd = (segments: EmaSegment[], end: SegmentPoint) => {
  const lastSegment = segments[segments.length - 1]
  if (!lastSegment) {
    return
  }

  lastSegment.end = { ...end }
}

const buildEmaSegments = (bars: EmaSegmentBar[], emaLength: number, minSegmentBars: number) => {
  const segments: EmaSegment[] = []
  let activeDirection: SegmentDirection | null = null
  let activeEnd: SegmentPoint | null = null
  let hasDrawableActiveSegment = false

  bars.forEach((bar) => {
    if (bar.index + 1 < emaLength || !isFiniteNumber(bar.ema)) {
      return
    }

    if (activeDirection === null || activeEnd === null) {
      if (bar.close < bar.ema) {
        activeDirection = 'down'
        activeEnd = getSegmentExtreme(bar, 'down')
      } else if (bar.close > bar.ema) {
        activeDirection = 'up'
        activeEnd = getSegmentExtreme(bar, 'up')
      }
      return
    }

    if (activeDirection === 'down') {
      if (bar.low < bar.ema && bar.low < activeEnd.price) {
        activeEnd = getSegmentExtreme(bar, 'down')
        if (hasDrawableActiveSegment) {
          updateLastSegmentEnd(segments, activeEnd)
        }
        return
      }

      if (bar.high > bar.ema && bar.index - activeEnd.index >= minSegmentBars) {
        const nextEnd = getSegmentExtreme(bar, 'up')
        const nextSegment = createSegment('up', activeEnd, nextEnd)

        segments.push(nextSegment)
        activeDirection = 'up'
        activeEnd = nextEnd
        hasDrawableActiveSegment = true
      }
      return
    }

    if (bar.high > bar.ema && bar.high > activeEnd.price) {
      activeEnd = getSegmentExtreme(bar, 'up')
      if (hasDrawableActiveSegment) {
        updateLastSegmentEnd(segments, activeEnd)
      }
      return
    }

    if (bar.low < bar.ema && bar.index - activeEnd.index >= minSegmentBars) {
      const nextEnd = getSegmentExtreme(bar, 'down')
      const nextSegment = createSegment('down', activeEnd, nextEnd)

      segments.push(nextSegment)
      activeDirection = 'down'
      activeEnd = nextEnd
      hasDrawableActiveSegment = true
    }
  })

  return segments
}

const getSegmentKey = (segment: EmaSegment) => {
  return `${segment.start.time}-${segment.direction}`
}

const getOffsetFromCurrentBar = (bars: EmaSegmentBar[], point: SegmentPoint) => {
  const lastBar = bars[bars.length - 1]
  if (!lastBar) {
    return 0
  }

  return point.index - lastBar.index
}

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
        if (!latestSegment) {
          return [Number.NaN, Number.NaN, Number.NaN]
        }

        const segmentColor = latestSegment.direction === 'up' ? 0 : 1
        const latestSegmentKey = getSegmentKey(latestSegment)
        if (this._state.emittedInitialStartKey !== latestSegmentKey) {
          this._state.emittedInitialStartKey = latestSegmentKey
          return [
            latestSegment.start.price,
            getOffsetFromCurrentBar(this._state.bars, latestSegment.start),
            segmentColor,
          ]
        }

        return [
          latestSegment.end.price,
          getOffsetFromCurrentBar(this._state.bars, latestSegment.end),
          segmentColor,
        ]
      }
    },
  },
])

export const localEmaSegmentStrategy = {
  getCustomIndicators,
  getLocalEmaSegmentIndicatorName,
}
