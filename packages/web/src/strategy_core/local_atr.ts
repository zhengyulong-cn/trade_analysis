type PineJsLike = {
  Std: {
    tr: (handleNaN: number | undefined, context: unknown) => number
    sma: (source: unknown, length: number, context: unknown) => number
  }
}

const LOCAL_ATR_INDICATOR_NAME = 'Local ATR'

const getLocalAtrIndicatorName = () => LOCAL_ATR_INDICATOR_NAME

const getCustomIndicators = (PineJS: PineJsLike) => Promise.resolve([
  {
    name: LOCAL_ATR_INDICATOR_NAME,
    metainfo: {
      _metainfoVersion: 53,
      id: `${LOCAL_ATR_INDICATOR_NAME}@tv-basicstudies-1`,
      description: LOCAL_ATR_INDICATOR_NAME,
      shortDescription: LOCAL_ATR_INDICATOR_NAME,
      isCustomIndicator: true,
      is_price_study: false,
      format: {
        type: 'price',
        precision: 2,
      },
      plots: [
        { id: 'atr', type: 'line' },
      ],
      styles: {
        atr: { title: 'ATR' },
      },
      defaults: {
        styles: {
          atr: {
            color: '#FF9800',
            linestyle: 0,
            linewidth: 1,
            plottype: 0,
            trackPrice: false,
            transparency: 0,
            visible: true,
          },
        },
        inputs: {
          length: 14,
        },
      },
      inputs: [
        {
          id: 'length',
          name: 'Length',
          defval: 14,
          type: 'integer',
          min: 1,
          max: 500,
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

        const length = Math.max(1, Number(input(0)) || 14)
        const trVal = PineJS.Std.tr(1, context)
        const trSeries = context.new_var(trVal)
        const atr = PineJS.Std.sma(trSeries, length, context)

        return [atr]
      }
    },
  },
])

export const localAtrStrategy = {
  getCustomIndicators,
  getLocalAtrIndicatorName,
}
