import {
  advanceBaseSegmentState,
  createEmptyBaseSegmentBuildState,
  getAllBaseSegments,
  getBaseSegmentKey,
  getOffsetFromCurrentBar,
  getLatestDrawableBaseSegment,
  isFiniteNumber,
  rebuildBaseSegmentState,
  upsertBar,
} from './base_segment_builder'
import {
  advanceTradingRangeState,
  consumeTradingRangeGraphicsRefresh,
  createEmptyTradingRangeBuildState,
  getAllTradingRanges,
  rebuildTradingRangeState,
} from './trading_range_builder'
import type {
  BaseSegmentBuildState,
  EmaSegmentBar,
  PineContextLike,
  PineJsLike,
  TradingRangeBuildState,
} from './types'

type LocalEmaSegmentStudyState = {
  bars: EmaSegmentBar[]
  emittedInitialDrawableSegmentStartKey: string | null
  emittedInitialHigherDrawableSegmentStartKey: string | null
  lastSettingsKey: string | null
  baseSegmentBuildState: BaseSegmentBuildState
  higherSegmentBuildState: BaseSegmentBuildState
  tradingRangeBuildState: TradingRangeBuildState
}

const LOCAL_EMA_SEGMENT_INDICATOR_NAME = 'Local EMA Segment'
const DEFAULT_EMA_LENGTH = 20
const DEFAULT_MIN_SEGMENT_BARS = 4
const DEFAULT_HIGHER_EMA_LENGTH = 120
const DEFAULT_HIGHER_MIN_SEGMENT_BARS = 24
const SEGMENT_LINE_WIDTH = 2
const TRADING_RANGE_POLYGON_STYLE_ID = 'tradingRange'

const createStudyState = (): LocalEmaSegmentStudyState => ({
  bars: [],
  emittedInitialDrawableSegmentStartKey: null,
  emittedInitialHigherDrawableSegmentStartKey: null,
  lastSettingsKey: null,
  baseSegmentBuildState: createEmptyBaseSegmentBuildState(),
  higherSegmentBuildState: createEmptyBaseSegmentBuildState(),
  tradingRangeBuildState: createEmptyTradingRangeBuildState(),
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
        { id: 'higherSegment', type: 'line' },
        { id: 'higherSegmentOffset', target: 'higherSegment', type: 'dataoffset' },
        { id: 'higherSegmentColor', palette: 'segmentPalette', target: 'higherSegment', type: 'colorer' },
      ],
      styles: {
        segment: {
          title: 'Segment',
          histogramBase: 0,
          joinPoints: false,
        },
        higherSegment: {
          title: 'Higher Segment',
          histogramBase: 0,
          joinPoints: false,
        },
      },
      graphics: {
        polygons: {
          [TRADING_RANGE_POLYGON_STYLE_ID]: {
            mouseTouchable: false,
            name: 'Trading Range',
            showBorder: true,
          },
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
          higherSegment: {
            color: '#F23645',
            linestyle: 0,
            linewidth: SEGMENT_LINE_WIDTH,
            plottype: 0,
            trackPrice: false,
            transparency: 0,
            visible: true,
          },
        },
        graphics: {
          polygons: {
            [TRADING_RANGE_POLYGON_STYLE_ID]: {
              color: '#2962FF',
              transparency: 85,
            },
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
          higherEmaLength: DEFAULT_HIGHER_EMA_LENGTH,
          higherMinSegmentBars: DEFAULT_HIGHER_MIN_SEGMENT_BARS,
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
        {
          id: 'higherEmaLength',
          name: 'Higher EMA Length',
          defval: DEFAULT_HIGHER_EMA_LENGTH,
          type: 'integer',
          min: 1,
          max: 500,
        },
        {
          id: 'higherMinSegmentBars',
          name: 'Higher Min Segment Bars',
          defval: DEFAULT_HIGHER_MIN_SEGMENT_BARS,
          type: 'integer',
          min: 1,
          max: 500,
        },
      ],
    },
    constructor: function (this: {
      _state?: LocalEmaSegmentStudyState
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
        const higherEmaLength = Math.max(1, Number(input(2)) || DEFAULT_HIGHER_EMA_LENGTH)
        const higherMinSegmentBars = Math.max(1, Number(input(3)) || DEFAULT_HIGHER_MIN_SEGMENT_BARS)
        const settingsKey = `${emaLength}:${minSegmentBars}:${higherEmaLength}:${higherMinSegmentBars}`
        const close = PineJS.Std.close(context)
        const closeSeries = context.new_var(close)
        const ema = PineJS.Std.ema(closeSeries, emaLength, context)
        const higherEma = PineJS.Std.ema(closeSeries, higherEmaLength, context)
        const time = PineJS.Std.time(context)
        const high = PineJS.Std.high(context)
        const low = PineJS.Std.low(context)
        let shouldRebuildBaseSegments = this._state.lastSettingsKey !== null && this._state.lastSettingsKey !== settingsKey
        let shouldRebuildHigherSegments = shouldRebuildBaseSegments
          || this._state.higherSegmentBuildState.processedBarCount > this._state.bars.length
        let shouldRebuildTradingRanges = shouldRebuildBaseSegments

        if (isFiniteNumber(time) && isFiniteNumber(close) && isFiniteNumber(high) && isFiniteNumber(low)) {
          const upsertResult = upsertBar(this._state.bars, {
            close,
            ema,
            higherEma,
            high,
            low,
            time,
          })

          shouldRebuildBaseSegments = shouldRebuildBaseSegments || upsertResult.type !== 'append'
          shouldRebuildHigherSegments = shouldRebuildHigherSegments || upsertResult.type !== 'append'
          shouldRebuildTradingRanges = shouldRebuildTradingRanges || upsertResult.type !== 'append'
        }

        this._state.lastSettingsKey = settingsKey

        if (shouldRebuildBaseSegments || this._state.baseSegmentBuildState.processedBarCount > this._state.bars.length) {
          this._state.baseSegmentBuildState = rebuildBaseSegmentState(this._state.bars, emaLength, minSegmentBars)
          shouldRebuildTradingRanges = true
        } else if (this._state.baseSegmentBuildState.processedBarCount < this._state.bars.length) {
          advanceBaseSegmentState(this._state.baseSegmentBuildState, this._state.bars, emaLength, minSegmentBars)
        }

        const latestBaseSegment = getLatestDrawableBaseSegment(this._state.baseSegmentBuildState)
        const higherBars = this._state.bars.map((bar) => ({
          ...bar,
          ema: bar.higherEma ?? Number.NaN,
        }))

        if (shouldRebuildHigherSegments || this._state.higherSegmentBuildState.processedBarCount > higherBars.length) {
          this._state.higherSegmentBuildState = rebuildBaseSegmentState(
            higherBars,
            higherEmaLength,
            higherMinSegmentBars,
          )
          shouldRebuildTradingRanges = true
        } else if (this._state.higherSegmentBuildState.processedBarCount < higherBars.length) {
          advanceBaseSegmentState(
            this._state.higherSegmentBuildState,
            higherBars,
            higherEmaLength,
            higherMinSegmentBars,
          )
        }

        const latestHigherSegment = getLatestDrawableBaseSegment(this._state.higherSegmentBuildState)
        const confirmedBaseSegments = this._state.baseSegmentBuildState.historicalBaseSegments
        const higherSegments = getAllBaseSegments(this._state.higherSegmentBuildState)

        if (
          shouldRebuildTradingRanges
          || this._state.tradingRangeBuildState.processedBaseSegmentCount > confirmedBaseSegments.length
        ) {
          this._state.tradingRangeBuildState = rebuildTradingRangeState(confirmedBaseSegments, higherSegments)
        } else if (this._state.tradingRangeBuildState.processedBaseSegmentCount < confirmedBaseSegments.length) {
          advanceTradingRangeState(this._state.tradingRangeBuildState, confirmedBaseSegments, higherSegments)
        }

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

        const higherSegmentOutput = (() => {
          if (!latestHigherSegment) {
            return [Number.NaN, Number.NaN, Number.NaN]
          }

          const higherSegmentColor = latestHigherSegment.direction === 'up' ? 0 : 1
          const latestHigherSegmentKey = getBaseSegmentKey(latestHigherSegment)

          if (this._state.emittedInitialHigherDrawableSegmentStartKey !== latestHigherSegmentKey) {
            this._state.emittedInitialHigherDrawableSegmentStartKey = latestHigherSegmentKey
            return [
              latestHigherSegment.start.price,
              getOffsetFromCurrentBar(this._state.bars, latestHigherSegment.start),
              higherSegmentColor,
            ]
          }

          return [
            latestHigherSegment.end.price,
            getOffsetFromCurrentBar(this._state.bars, latestHigherSegment.end),
            higherSegmentColor,
          ]
        })()

        const seriesOutput = [
          ...baseSegmentOutput,
          ...higherSegmentOutput,
        ]

        const shouldEmitTradingRangeGraphics = context.symbol?.isLastBar && (
          shouldRebuildTradingRanges || consumeTradingRangeGraphicsRefresh(this._state.tradingRangeBuildState)
        )

        if (!shouldEmitTradingRangeGraphics) {
          return seriesOutput
        }

        const graphData = getAllTradingRanges(this._state.tradingRangeBuildState).map((range, i) => ({
          id: `${range.left.time}-${range.right.time}-${i}`,
          points: [
            { index: range.left.time, level: range.top },
            { index: range.right.time, level: range.top },
            { index: range.right.time, level: range.bottom },
            { index: range.left.time, level: range.bottom },
          ],
        }))

        const tradingRangeGraphics = {
          nonseries: true,
          type: 'study_graphics',
          data: {
            graphicsCmds: {
              create: {
                polygons: [
                  {
                    styleId: TRADING_RANGE_POLYGON_STYLE_ID,
                    data: graphData,
                  },
                ],
              },
              erase: [{ action: 'all' }],
            },
          },
        }

        return {
          type: 'composite',
          data: [
            seriesOutput,
            tradingRangeGraphics,
          ],
        }
      }
    },
  },
])

export const localEmaSegmentStrategy = {
  getCustomIndicators,
  getLocalEmaSegmentIndicatorName,
}
