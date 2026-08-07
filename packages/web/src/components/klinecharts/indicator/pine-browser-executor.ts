import { normalizePineResult, type PineAlert, type PineBar, type PineNormalizedResult } from "@trade-analysis/core"
import type { KLineData } from "klinecharts"
import { PineTS } from "pinets"

import type {
  PineIndicatorDrawings,
  PineIndicatorPlot,
  PineIndicatorPlotPoint,
  PineScript,
} from "@/api/modules"

export interface LocalPineIndicatorResult {
  scriptId: number
  scriptName: string
  overlay: boolean
  plots: PineIndicatorPlot[]
  drawings: PineIndicatorDrawings
  alerts: PineAlert[]
}

const toMilliseconds = (value: number) => (value < 100_000_000_000 ? value * 1000 : value)

const toPineBars = (dataList: KLineData[]): PineBar[] => dataList.map((bar) => ({
  openTime: bar.timestamp,
  closeTime: bar.timestamp,
  open: bar.open,
  high: bar.high,
  low: bar.low,
  close: bar.close,
  volume: Number.isFinite(bar.volume) ? bar.volume as number : 0,
}))

const asRecord = (value: unknown): Record<string, unknown> | undefined => (
  typeof value === "object" && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : undefined
)

const getOverlay = (indicator: unknown) => asRecord(indicator)?.overlay === true

const toPlotPoint = (value: unknown): PineIndicatorPlotPoint | undefined => {
  const point = asRecord(value)
  if (!point || !Number.isFinite(point.time)) {
    return undefined
  }

  const options = asRecord(point.options)
  return {
    time: toMilliseconds(point.time as number),
    value: Number.isFinite(point.value) ? point.value as number : null,
    ...(typeof point.title === "string" ? { title: point.title } : {}),
    ...(!options ? {} : {
      options: {
        ...(typeof options.color === "string" ? { color: options.color } : {}),
        ...(Number.isFinite(options.linewidth) ? { linewidth: options.linewidth as number } : {}),
        ...(typeof options.style === "string" ? { style: options.style } : {}),
      },
    }),
  }
}

const toPlots = (result: PineNormalizedResult): PineIndicatorPlot[] => result.plots.map((plot) => ({
  key: plot.key,
  ...(plot.title ? { title: plot.title } : {}),
  ...(asRecord(plot.options) ? { options: asRecord(plot.options) } : {}),
  data: plot.data.flatMap((value) => {
    const point = toPlotPoint(value)
    return point ? [point] : []
  }),
}))

export const executePineScriptInBrowser = async (
  script: PineScript,
  dataList: KLineData[],
): Promise<LocalPineIndicatorResult> => {
  if (!dataList.length) {
    throw new Error("No K-line data is available for Pine indicator execution.")
  }

  const bars = toPineBars(dataList)
  const context = await new PineTS(bars).run(script.script_content)
  const result = normalizePineResult({
    indicator: context.indicator,
    plots: context.plots,
    alerts: context.alerts,
    warnings: context.warnings,
  }, bars)

  console.log(result)

  return {
    scriptId: script.script_id,
    scriptName: script.script_name,
    overlay: getOverlay(result.indicator),
    plots: toPlots(result),
    drawings: result.drawings as unknown as PineIndicatorDrawings,
    alerts: result.alerts,
  }
}
