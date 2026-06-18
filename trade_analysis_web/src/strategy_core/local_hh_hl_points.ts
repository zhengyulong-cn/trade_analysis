type PineJsLike = {
  Std: {
    high: (context: unknown) => number
    low: (context: unknown) => number
    time: (context: unknown) => number
  }
}

type PineContextLike = {
  symbol?: {
    isLastBar?: boolean
  }
}

type RawBar = {
  high: number
  low: number
  time: number
  index: number
}

type PivotDirection = 1 | -1
type SignalKind = 'HH' | 'HL' | 'LL' | 'LH'

type PivotPoint = {
  direction: PivotDirection
  index: number
  price: number
}

type SignalPoint = {
  confirmedOnIndex: number
  index: number
  kind: SignalKind
  price: number
}

type StudyState = {
  bars: RawBar[]
  signals: SignalPoint[]
}

const LOCAL_HH_HL_POINTS_INDICATOR_NAME = 'Local HH HL Points'
const DEFAULT_LEFT_BARS = 5
const DEFAULT_RIGHT_BARS = 5

const HH_COLOR = '#22AB94'
const HL_COLOR = '#8BC34A'
const LL_COLOR = '#F23645'
const LH_COLOR = '#FF9800'

const getLocalHhHlPointsIndicatorName = () => LOCAL_HH_HL_POINTS_INDICATOR_NAME

const createStudyState = (): StudyState => ({
  bars: [],
  signals: [],
})

const isFiniteNumber = (value: unknown): value is number => {
  return typeof value === 'number' && Number.isFinite(value)
}

const upsertBar = (bars: RawBar[], nextBar: Omit<RawBar, 'index'>) => {
  const lastBar = bars[bars.length - 1]

  if (!lastBar || nextBar.time > lastBar.time) {
    bars.push({
      ...nextBar,
      index: bars.length,
    })
    return { index: bars.length - 1, type: 'append' as const }
  }

  if (nextBar.time === lastBar.time) {
    bars[bars.length - 1] = {
      ...nextBar,
      index: lastBar.index,
    }
    return { index: lastBar.index, type: 'replace_last' as const }
  }

  const existingIndex = bars.findIndex((bar) => bar.time === nextBar.time)
  if (existingIndex >= 0) {
    bars[existingIndex] = {
      ...nextBar,
      index: existingIndex,
    }
    return { index: existingIndex, type: 'replace_existing' as const }
  }

  bars.push({
    ...nextBar,
    index: bars.length,
  })
  bars.sort((first, second) => first.time - second.time)
  bars.forEach((bar, index) => {
    bar.index = index
  })

  return {
    index: bars.findIndex((bar) => bar.time === nextBar.time),
    type: 'insert_historical' as const,
  }
}

const isPivotHigh = (bars: RawBar[], pivotIndex: number, leftBars: number, rightBars: number) => {
  const pivotBar = bars[pivotIndex]
  if (!pivotBar) {
    return false
  }

  for (let offset = 1; offset <= leftBars; offset += 1) {
    const bar = bars[pivotIndex - offset]
    if (!bar || bar.high >= pivotBar.high) {
      return false
    }
  }

  for (let offset = 1; offset <= rightBars; offset += 1) {
    const bar = bars[pivotIndex + offset]
    if (!bar || bar.high > pivotBar.high) {
      return false
    }
  }

  return true
}

const isPivotLow = (bars: RawBar[], pivotIndex: number, leftBars: number, rightBars: number) => {
  const pivotBar = bars[pivotIndex]
  if (!pivotBar) {
    return false
  }

  for (let offset = 1; offset <= leftBars; offset += 1) {
    const bar = bars[pivotIndex - offset]
    if (!bar || bar.low <= pivotBar.low) {
      return false
    }
  }

  for (let offset = 1; offset <= rightBars; offset += 1) {
    const bar = bars[pivotIndex + offset]
    if (!bar || bar.low < pivotBar.low) {
      return false
    }
  }

  return true
}

const classifySignal = (pivots: PivotPoint[], currentIndex: number): SignalKind | null => {
  const a = pivots[currentIndex]
  const b = pivots[currentIndex - 1]
  const c = pivots[currentIndex - 2]
  const d = pivots[currentIndex - 3]
  const e = pivots[currentIndex - 4]

  if (!a || !b || !c || !d) {
    return null
  }

  const isHh = a.price > b.price && a.price > c.price && c.price > b.price && c.price > d.price
  if (isHh) {
    return 'HH'
  }

  const isLl = a.price < b.price && a.price < c.price && c.price < b.price && c.price < d.price
  if (isLl) {
    return 'LL'
  }

  const isHl = (
    (a.price >= c.price && !!e && b.price > c.price && b.price > d.price && d.price > c.price && d.price > e.price)
    || (a.price < b.price && a.price > c.price && b.price < d.price)
  )
  if (isHl) {
    return 'HL'
  }

  const isLh = (
    (a.price <= c.price && !!e && b.price < c.price && b.price < d.price && d.price < c.price && d.price < e.price)
    || (a.price > b.price && a.price < c.price && b.price > d.price)
  )
  if (isLh) {
    return 'LH'
  }

  return null
}

const buildSignals = (bars: RawBar[], leftBars: number, rightBars: number) => {
  const pivots: PivotPoint[] = []
  const signals: SignalPoint[] = []

  for (let pivotIndex = leftBars; pivotIndex + rightBars < bars.length; pivotIndex += 1) {
    const pivotHigh = isPivotHigh(bars, pivotIndex, leftBars, rightBars)
    const pivotLow = isPivotLow(bars, pivotIndex, leftBars, rightBars)

    let nextPivot: PivotPoint | null = null
    if (pivotHigh) {
      nextPivot = {
        direction: 1,
        index: pivotIndex,
        price: bars[pivotIndex].high,
      }
    } else if (pivotLow) {
      nextPivot = {
        direction: -1,
        index: pivotIndex,
        price: bars[pivotIndex].low,
      }
    }

    if (!nextPivot) {
      continue
    }

    const previousPivot = pivots[pivots.length - 1]
    if (previousPivot?.direction === nextPivot.direction) {
      const shouldReplace = nextPivot.direction === 1
        ? nextPivot.price > previousPivot.price
        : nextPivot.price < previousPivot.price

      if (shouldReplace) {
        pivots[pivots.length - 1] = nextPivot
      }
      continue
    }

    pivots.push(nextPivot)
    const kind = classifySignal(pivots, pivots.length - 1)
    if (kind) {
      signals.push({
        confirmedOnIndex: nextPivot.index + rightBars,
        index: nextPivot.index,
        kind,
        price: nextPivot.price,
      })
    }
  }

  return signals
}

const getConfirmedSignalByKind = (
  signals: SignalPoint[],
  confirmedOnIndex: number,
  kind: SignalKind,
) => {
  for (let index = signals.length - 1; index >= 0; index -= 1) {
    const signal = signals[index]
    if (signal.kind === kind && signal.confirmedOnIndex === confirmedOnIndex) {
      return signal
    }
  }

  return null
}

const getCustomIndicators = (PineJS: PineJsLike) => Promise.resolve([
  {
    name: LOCAL_HH_HL_POINTS_INDICATOR_NAME,
    metainfo: {
      _metainfoVersion: 53,
      id: `${LOCAL_HH_HL_POINTS_INDICATOR_NAME}@tv-basicstudies-1`,
      description: LOCAL_HH_HL_POINTS_INDICATOR_NAME,
      shortDescription: 'HH HL LL LH',
      isCustomIndicator: true,
      is_price_study: true,
      linkedToSeries: true,
      format: {
        type: 'price',
        precision: 2,
      },
      plots: [
        { id: 'hh', type: 'shapes' },
        { id: 'hhOffset', target: 'hh', type: 'dataoffset' },
        { id: 'hl', type: 'shapes' },
        { id: 'hlOffset', target: 'hl', type: 'dataoffset' },
        { id: 'll', type: 'shapes' },
        { id: 'llOffset', target: 'll', type: 'dataoffset' },
        { id: 'lh', type: 'shapes' },
        { id: 'lhOffset', target: 'lh', type: 'dataoffset' },
      ],
      styles: {
        hh: {
          title: 'Higher High',
          text: 'HH',
          size: 'small',
        },
        hl: {
          title: 'Higher Low',
          text: 'HL',
          size: 'small',
        },
        ll: {
          title: 'Lower Low',
          text: 'LL',
          size: 'small',
        },
        lh: {
          title: 'Lower High',
          text: 'LH',
          size: 'small',
        },
      },
      defaults: {
        styles: {
          hh: {
            color: HH_COLOR,
            location: 'Absolute',
            plottype: 'shape_label_down',
            textColor: '#000000',
            transparency: 0,
            visible: true,
          },
          hl: {
            color: HL_COLOR,
            location: 'Absolute',
            plottype: 'shape_label_up',
            textColor: '#000000',
            transparency: 0,
            visible: true,
          },
          ll: {
            color: LL_COLOR,
            location: 'Absolute',
            plottype: 'shape_label_up',
            textColor: '#FFFFFF',
            transparency: 0,
            visible: true,
          },
          lh: {
            color: LH_COLOR,
            location: 'Absolute',
            plottype: 'shape_label_down',
            textColor: '#000000',
            transparency: 0,
            visible: true,
          },
        },
        inputs: {
          leftBars: DEFAULT_LEFT_BARS,
          rightBars: DEFAULT_RIGHT_BARS,
          showHH: true,
          showHL: true,
          showLL: true,
          showLH: true,
        },
      },
      inputs: [
        {
          id: 'leftBars',
          name: 'Left Bars',
          defval: DEFAULT_LEFT_BARS,
          type: 'integer',
          min: 1,
          max: 100,
        },
        {
          id: 'rightBars',
          name: 'Right Bars',
          defval: DEFAULT_RIGHT_BARS,
          type: 'integer',
          min: 1,
          max: 100,
        },
        {
          id: 'showHH',
          name: 'Show HH',
          defval: true,
          type: 'bool',
        },
        {
          id: 'showHL',
          name: 'Show HL',
          defval: true,
          type: 'bool',
        },
        {
          id: 'showLL',
          name: 'Show LL',
          defval: true,
          type: 'bool',
        },
        {
          id: 'showLH',
          name: 'Show LH',
          defval: true,
          type: 'bool',
        },
      ],
    },
    constructor: function (this: {
      _state?: StudyState
      init?: (context: PineContextLike, input: (index: number) => number | boolean) => void
      main?: (context: PineContextLike, input: (index: number) => number | boolean) => number[]
    }) {
      this.init = function () {
        this._state = createStudyState()
      }

      this.main = function (context, input) {
        if (!this._state) {
          this._state = createStudyState()
        }

        const high = PineJS.Std.high(context)
        const low = PineJS.Std.low(context)
        const time = PineJS.Std.time(context)
        const leftBars = Math.max(1, Number(input(0)) || DEFAULT_LEFT_BARS)
        const rightBars = Math.max(1, Number(input(1)) || DEFAULT_RIGHT_BARS)
        const showHH = Boolean(input(2))
        const showHL = Boolean(input(3))
        const showLL = Boolean(input(4))
        const showLH = Boolean(input(5))

        if (isFiniteNumber(high) && isFiniteNumber(low) && isFiniteNumber(time)) {
          upsertBar(this._state.bars, { high, low, time })
          this._state.signals = buildSignals(this._state.bars, leftBars, rightBars)
        }

        const currentBarIndex = this._state.bars[this._state.bars.length - 1]?.index
        const hhSignal = showHH && typeof currentBarIndex === 'number'
          ? getConfirmedSignalByKind(this._state.signals, currentBarIndex, 'HH')
          : null
        const hlSignal = showHL && typeof currentBarIndex === 'number'
          ? getConfirmedSignalByKind(this._state.signals, currentBarIndex, 'HL')
          : null
        const llSignal = showLL && typeof currentBarIndex === 'number'
          ? getConfirmedSignalByKind(this._state.signals, currentBarIndex, 'LL')
          : null
        const lhSignal = showLH && typeof currentBarIndex === 'number'
          ? getConfirmedSignalByKind(this._state.signals, currentBarIndex, 'LH')
          : null

        return [
          hhSignal?.price ?? Number.NaN,
          hhSignal ? -rightBars : Number.NaN,
          hlSignal?.price ?? Number.NaN,
          hlSignal ? -rightBars : Number.NaN,
          llSignal?.price ?? Number.NaN,
          llSignal ? -rightBars : Number.NaN,
          lhSignal?.price ?? Number.NaN,
          lhSignal ? -rightBars : Number.NaN,
        ]
      }
    },
  },
])

export const localHhHlPointsStrategy = {
  getCustomIndicators,
  getLocalHhHlPointsIndicatorName,
}
