type PineJsLike = {
  Std: {
    close: (context: unknown) => number
    sma: (source: unknown, length: number, context: unknown) => number
    stdev: (source: unknown, length: number, context: unknown) => number
  }
}

const LOCAL_BOLL_INDICATOR_NAME = 'Local BOLL'

const getLocalBollIndicatorName = () => LOCAL_BOLL_INDICATOR_NAME

const getCustomIndicators = (PineJS: PineJsLike) => Promise.resolve([
  {
    name: LOCAL_BOLL_INDICATOR_NAME,
    metainfo: {
      _metainfoVersion: 53,
      id: `${LOCAL_BOLL_INDICATOR_NAME}@tv-basicstudies-1`,
      description: LOCAL_BOLL_INDICATOR_NAME,
      shortDescription: LOCAL_BOLL_INDICATOR_NAME,
      isCustomIndicator: true,
      is_price_study: true,
      linkedToSeries: true,
      format: {
        type: 'price',
        precision: 2,
      },
      plots: [
        { id: 'basis', type: 'line' },
        { id: 'upper', type: 'line' },
        { id: 'lower', type: 'line' },
      ],
      styles: {
        basis: { title: 'Basis' },
        upper: { title: 'Upper' },
        lower: { title: 'Lower' },
      },
      defaults: {
        styles: {
          basis: {
            color: '#2962FF',
            linestyle: 0,
            linewidth: 1,
            plottype: 0,
            trackPrice: false,
            transparency: 0,
            visible: true,
          },
          upper: {
            color: '#F23645',
            linestyle: 0,
            linewidth: 1,
            plottype: 0,
            trackPrice: false,
            transparency: 0,
            visible: true,
          },
          lower: {
            color: '#089981',
            linestyle: 0,
            linewidth: 1,
            plottype: 0,
            trackPrice: false,
            transparency: 0,
            visible: true,
          },
        },
        inputs: {
          length: 20,
          mult: 2,
        },
      },
      inputs: [
        {
          id: 'length',
          name: 'Length',
          defval: 20,
          type: 'integer',
          min: 1,
          max: 500,
        },
        {
          id: 'mult',
          name: 'StdDev',
          defval: 2,
          type: 'float',
          min: 0.1,
          max: 50,
        },
      ],
    },
    constructor: function (this: {
      _context?: { new_var: (value?: number) => unknown }
      _input?: (index: number) => number
      init?: (context: { new_var: (value?: number) => unknown }, input: (index: number) => number) => void
      main?: (context: { new_var: (value?: number) => unknown }, input: (index: number) => number) => number[]
    }) {
      this.init = function (context, input) {
        this._context = context
        this._input = input
      }

      this.main = function (context, input) {
        this._context = context
        this._input = input

        const length = Math.max(1, Number(input(0)) || 20)
        const multiplier = Number(input(1)) || 2
        const close = PineJS.Std.close(context)
        const closeSeries = context.new_var(close)
        const basis = PineJS.Std.sma(closeSeries, length, context)
        const deviation = PineJS.Std.stdev(closeSeries, length, context) * multiplier

        return [
          basis,
          basis + deviation,
          basis - deviation,
        ]
      }
    },
  },
])

export const localBollStrategy = {
  getCustomIndicators,
  getLocalBollIndicatorName,
}