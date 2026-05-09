import axios from '@/api/axios'
import type { FractalPoint, FractalListResponse } from '@/api/modules/analysis'
import type { TradingViewWidget } from '@/components/charts/tradingViewTypes'

export interface SegmentData {
  direction: 'up' | 'down'
  start: { index: number; time: number; price: number }
  end: { index: number; time: number; price: number }
}

export interface TradingRangeData {
  top: number
  bottom: number
  left: { index: number; time: number; price: number }
  right: { index: number; time: number; price: number }
}

interface AnalysisResponse extends FractalListResponse {
  segments: SegmentData[]
  higher_segments: SegmentData[]
  trading_ranges: TradingRangeData[]
}

const UP_COLOR = '#CC0000'
const DOWN_COLOR = '#00AA00'
const TOP_COLOR = '#CC0000'
const BOTTOM_COLOR = '#00AA00'
const HIGHER_UP_COLOR = '#FF00FF'
const HIGHER_DOWN_COLOR = '#0000FF'
const SEGMENT_LINE_WIDTH = 2
const HIGHER_LINE_WIDTH = 3
const TRADING_RANGE_COLOR = '#FFCC00'

export function useAnalysisDrawer() {
  let drawGeneration = 0

  const fetchAnalysis = async (symbol: string, interval: number) => {
    const data = await axios.get<AnalysisResponse>('/analysis', { symbol, interval }) as unknown as AnalysisResponse
    return data
  }

  const clearAll = (widget: TradingViewWidget | null) => {
    if (!widget) return
    try { widget.activeChart().removeAllShapes() } catch { /* ignore */ }
  }

  const drawSegments = (widget: TradingViewWidget, segments: SegmentData[]) => {
    const chart = widget.activeChart()
    for (const seg of segments) {
      const color = seg.direction === 'up' ? UP_COLOR : DOWN_COLOR
      chart.createMultipointShape(
        [
          { time: seg.start.time, price: seg.start.price },
          { time: seg.end.time, price: seg.end.price },
        ],
        {
          shape: 'polyline',
          lock: true,
          disableSelection: true,
          disableSave: true,
          overrides: {
            linecolor: color,
            linewidth: SEGMENT_LINE_WIDTH,
            linestyle: 0,
          },
        },
      )
    }
  }

  const drawFractals = (widget: TradingViewWidget, fractals: FractalPoint[]) => {
    const chart = widget.activeChart()
    for (const f of fractals) {
      const isTop = f.type === 'top'
      chart.createShape(
        { time: f.time, price: f.price },
        {
          shape: isTop ? 'arrow_down' : 'arrow_up',
          text: isTop ? '顶' : '底',
          lock: true,
          disableSelection: true,
          disableSave: true,
          overrides: {
            arrowcolor: isTop ? TOP_COLOR : BOTTOM_COLOR,
            textcolor: isTop ? TOP_COLOR : BOTTOM_COLOR,
            fontsize: 10,
          },
        },
      )
    }
  }

  const drawHigherSegments = (widget: TradingViewWidget, segments: SegmentData[]) => {
    const chart = widget.activeChart()
    for (const seg of segments) {
      const color = seg.direction === 'up' ? HIGHER_UP_COLOR : HIGHER_DOWN_COLOR
      chart.createMultipointShape(
        [
          { time: seg.start.time, price: seg.start.price },
          { time: seg.end.time, price: seg.end.price },
        ],
        {
          shape: 'polyline',
          lock: true,
          disableSelection: true,
          disableSave: true,
          overrides: {
            linecolor: color,
            linewidth: HIGHER_LINE_WIDTH,
            linestyle: 0,
          },
        },
      )
    }
  }

  const drawTradingRanges = (widget: TradingViewWidget, ranges: TradingRangeData[]) => {
    const chart = widget.activeChart()
    for (const r of ranges) {
      const lb = { time: r.left.time, price: r.bottom }
      const rt = { time: r.right.time, price: r.top }
      chart.createMultipointShape(
        [lb, rt],
        {
          shape: 'rectangle',
          lock: true,
          disableSelection: true,
          disableSave: true,
          overrides: {
            linecolor: TRADING_RANGE_COLOR,
            fillbackground: TRADING_RANGE_COLOR,
            transparency: 80,
            linewidth: 1,
          },
        },
      )
    }
  }

  const fetchAndDraw = async (
    widget: TradingViewWidget | null,
    symbol: string,
    interval: number,
  ) => {
    if (!widget || !symbol || !interval) return

    const gen = ++drawGeneration

    try {
      const data = await fetchAnalysis(symbol, interval)
      if (gen !== drawGeneration || !widget) return

      clearAll(widget)
      if (gen !== drawGeneration || !widget) return

      drawSegments(widget, data.segments)
      drawHigherSegments(widget, data.higher_segments)
      drawTradingRanges(widget, data.trading_ranges)
    } catch {
      // silently ignore
    }
  }

  return {
    clearAll,
    fetchAndDraw,
  }
}
