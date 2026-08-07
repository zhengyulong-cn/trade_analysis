import { registerIndicator, type Chart, type IndicatorFigure, type KLineData } from "klinecharts"

import type { PineIndicatorPlot } from "@/api/modules"
import type { LocalPineIndicatorResult } from "./pine-browser-executor"

type PineIndicatorValues = Record<string, number | null | PinePlotStyles>
type PinePlotStyles = Record<string, { color?: string; lineWidth?: number }>

const registeredIndicatorNames = new Set<string>()
const resultByIndicatorName = new Map<string, LocalPineIndicatorResult>()

const indicatorName = (scriptId: number) => `PINE_${scriptId}`

const getPlotColor = (plot: PineIndicatorPlot) => (
  plot.data.find((item) => typeof item.options?.color === "string")?.options?.color ?? "#2962ff"
)

const getPlotLineWidth = (plot: PineIndicatorPlot) => {
  const lineWidth = plot.data.find((item) => Number.isFinite(item.options?.linewidth))?.options?.linewidth
  return lineWidth === undefined ? 2 : Math.max(1, lineWidth)
}

const isHistogram = (plot: PineIndicatorPlot) => {
  const style = plot.options?.style ?? plot.data.find((item) => item.options?.style)?.options?.style
  return typeof style === "string" && style.includes("histogram")
}

const toValuesByTimestamp = (plots: PineIndicatorPlot[]) => {
  const values = new Map<number, PineIndicatorValues>()
  for (const plot of plots) {
    for (const point of plot.data) {
      if (!Number.isFinite(point.time)) {
        continue
      }
      const item = values.get(point.time) ?? {}
      item[plot.key] = Number.isFinite(point.value) ? point.value as number : null
      if (point.options?.color || Number.isFinite(point.options?.linewidth)) {
        const styles = item.__pineStyles as PinePlotStyles | undefined ?? {}
        styles[plot.key] = {
          ...(point.options?.color ? { color: point.options.color } : {}),
          ...(Number.isFinite(point.options?.linewidth) ? { lineWidth: point.options?.linewidth as number } : {}),
        }
        item.__pineStyles = styles
      }
      values.set(point.time, item)
    }
  }
  return values
}

const createFigures = (result: LocalPineIndicatorResult): Array<IndicatorFigure<PineIndicatorValues>> => {
  return result.plots.map((plot) => ({
    key: plot.key,
    title: `${plot.title ?? plot.key}: `,
    type: isHistogram(plot) ? "bar" : "line",
    ...(isHistogram(plot) ? { baseValue: 0 } : {}),
    styles: ({ data }) => {
      const styles = data.current?.__pineStyles as PinePlotStyles | undefined
      const pointStyle = styles?.[plot.key]
      const color = pointStyle?.color ?? getPlotColor(plot)
      if (isHistogram(plot)) {
        return { style: "fill", color, borderColor: color }
      }
      return {
        style: "solid",
        color,
        size: pointStyle?.lineWidth ?? getPlotLineWidth(plot),
      }
    },
  }))
}

export const registerPineIndicator = (result: LocalPineIndicatorResult) => {
  const name = indicatorName(result.scriptId)
  resultByIndicatorName.set(name, result)
  if (registeredIndicatorNames.has(name)) {
    return name
  }

  registerIndicator<PineIndicatorValues>({
    name,
    shortName: result.scriptName,
    series: result.overlay ? "price" : "normal",
    shouldOhlc: result.overlay,
    calcParams: [],
    regenerateFigures: () => createFigures(resultByIndicatorName.get(name) ?? result),
    calc: (dataList: KLineData[], indicator) => {
      const latestResult = resultByIndicatorName.get(indicator.name)
      const valuesByTimestamp = toValuesByTimestamp(latestResult?.plots ?? [])
      return dataList.map((bar) => valuesByTimestamp.get(bar.timestamp) ?? {})
    },
  })
  registeredIndicatorNames.add(name)
  return name
}

export const createPineIndicator = (chart: Chart, result: LocalPineIndicatorResult) => {
  const name = registerPineIndicator(result)
  chart.removeIndicator({ name })
  return chart.createIndicator(result.overlay ? { name, paneId: "candle_pane" } : { name }, true) !== null
}

export const removePineIndicator = (chart: Chart | null, scriptId: number) => {
  const name = indicatorName(scriptId)
  resultByIndicatorName.delete(name)
  chart?.removeIndicator({ name })
}
