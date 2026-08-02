export interface PineBar {
  openTime: number
  closeTime?: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface PineRawResult {
  indicator: unknown
  plots: unknown
  warnings: unknown
}

export interface PinePlot {
  key: string
  title?: string
  options?: unknown
  data: unknown[]
}

export interface PineDrawings {
  labels: Array<Record<string, unknown>>
  lines: Array<Record<string, unknown>>
  boxes: Array<Record<string, unknown>>
}

export interface PineNormalizedResult {
  indicator: unknown
  plots: PinePlot[]
  drawings: PineDrawings
  warnings: unknown
}

type PinePlots = Record<string, unknown>

type PlotEntry = {
  title?: unknown
  option?: unknown
  options?: unknown
  data?: unknown
}

const toMilliseconds = (value: number) => (value < 100_000_000_000 ? value * 1000 : value)

const asRecord = (value: unknown): Record<string, unknown> | undefined =>
  typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined

const asArray = (value: unknown): unknown[] => (Array.isArray(value) ? value : [])

const asFiniteNumber = (value: unknown): number | undefined =>
  typeof value === "number" && Number.isFinite(value) ? value : undefined

const resolveCoordinate = (value: unknown, xloc: unknown, bars: PineBar[]) => {
  const coordinate = asFiniteNumber(value)
  if (coordinate === undefined) {
    return {}
  }

  if (xloc === "bar_time") {
    return { timestamp: toMilliseconds(coordinate) }
  }

  const barIndex = Number.isInteger(coordinate) ? coordinate : undefined
  const timestamp = barIndex === undefined ? undefined : bars[barIndex]?.openTime
  return {
    ...(barIndex === undefined ? {} : { barIndex }),
    ...(timestamp === undefined ? {} : { timestamp }),
  }
}

const collectDrawingData = (plots: PinePlots, name: string) => {
  const collection = asRecord(plots[name])
  if (!collection) {
    return []
  }

  const entries = "data" in collection ? [[name, collection] as const] : Object.entries(collection)
  return entries.flatMap(([key, value]) => {
    const entry = asRecord(value) as PlotEntry | undefined
    return asArray(entry?.data).flatMap((sample) => {
      const sampleRecord = asRecord(sample)
      const drawingValues = sampleRecord && "value" in sampleRecord
        ? asArray(sampleRecord.value)
        : [sample]

      return drawingValues.map((item) => ({ key, title: entry?.title, item }))
    })
  })
}

const normalizePlots = (plots: PinePlots): PinePlot[] =>
  Object.entries(plots)
    .filter(([key]) => !key.startsWith("__"))
    .map(([key, value]) => {
      const entry = asRecord(value) as PlotEntry | undefined
      return {
        key,
        ...(typeof entry?.title === "string" ? { title: entry.title } : {}),
        ...(
          entry?.options === undefined && entry?.option === undefined
            ? {}
            : { options: entry.options ?? entry.option }
        ),
        data: asArray(entry?.data),
      }
    })

const normalizeDrawings = (plots: PinePlots, bars: PineBar[]): PineDrawings => ({
  labels: collectDrawingData(plots, "__labels__").flatMap(({ key, title, item }, index) => {
    const label = asRecord(item)
    if (!label || label._deleted === true) {
      return []
    }

    return [{
      id: `${key}-${label.id ?? index}`,
      ...(typeof title === "string" ? { title } : {}),
      ...resolveCoordinate(label.x, label.xloc, bars),
      ...(asFiniteNumber(label.y) === undefined ? {} : { price: label.y }),
      ...(typeof label.text === "string" ? { text: label.text } : {}),
      ...(typeof label.style === "string" ? { style: label.style } : {}),
      ...(typeof label.color === "string" ? { color: label.color } : {}),
      ...(typeof label.textcolor === "string" ? { textColor: label.textcolor } : {}),
    }]
  }),
  lines: collectDrawingData(plots, "__lines__").flatMap(({ key, title, item }, index) => {
    const line = asRecord(item)
    if (!line || line._deleted === true) {
      return []
    }

    return [{
      id: `${key}-${line.id ?? index}`,
      ...(typeof title === "string" ? { title } : {}),
      start: {
        ...resolveCoordinate(line.x1, line.xloc, bars),
        ...(asFiniteNumber(line.y1) === undefined ? {} : { price: line.y1 }),
      },
      end: {
        ...resolveCoordinate(line.x2, line.xloc, bars),
        ...(asFiniteNumber(line.y2) === undefined ? {} : { price: line.y2 }),
      },
      ...(typeof line.extend === "string" ? { extend: line.extend } : {}),
      ...(typeof line.style === "string" ? { style: line.style } : {}),
      ...(typeof line.color === "string" ? { color: line.color } : {}),
      ...(asFiniteNumber(line.width) === undefined ? {} : { width: line.width }),
    }]
  }),
  boxes: collectDrawingData(plots, "__boxes__").flatMap(({ key, title, item }, index) => {
    const box = asRecord(item)
    if (!box || box._deleted === true) {
      return []
    }

    return [{
      id: `${key}-${box.id ?? index}`,
      ...(typeof title === "string" ? { title } : {}),
      start: resolveCoordinate(box.left, box.xloc, bars),
      end: resolveCoordinate(box.right, box.xloc, bars),
      ...(asFiniteNumber(box.top) === undefined ? {} : { top: box.top }),
      ...(asFiniteNumber(box.bottom) === undefined ? {} : { bottom: box.bottom }),
      ...(typeof box.extend === "string" ? { extend: box.extend } : {}),
      ...(typeof box.border_color === "string" ? { borderColor: box.border_color } : {}),
      ...(typeof box.border_style === "string" ? { borderStyle: box.border_style } : {}),
      ...(asFiniteNumber(box.border_width) === undefined ? {} : { borderWidth: box.border_width }),
      ...(typeof box.bgcolor === "string" ? { backgroundColor: box.bgcolor } : {}),
      ...(typeof box.text === "string" ? { text: box.text } : {}),
    }]
  }),
})

export const normalizePineResult = (result: PineRawResult, bars: PineBar[]): PineNormalizedResult => {
  const plots = asRecord(result.plots) ?? {}
  return {
    indicator: result.indicator,
    plots: normalizePlots(plots),
    drawings: normalizeDrawings(plots, bars),
    warnings: result.warnings,
  }
}
