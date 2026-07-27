import { PineTS } from 'pinets'

import { PineExecutionError } from '../errors/pine-execution-error.js'

export type PineInputBar = {
  timestamp?: number
  openTime?: number
  closeTime?: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export type ExecutePineRequest = {
  source: string
  bars: PineInputBar[]
}

type PineBar = {
  openTime: number
  closeTime?: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

type PinePlots = Record<string, unknown>

type PlotEntry = {
  title?: unknown
  option?: unknown
  data?: unknown
}

const toMilliseconds = (value: number) => (value < 100_000_000_000 ? value * 1000 : value)

const normalizeBars = (bars: PineInputBar[]): PineBar[] =>
  bars.map((bar, index) => {
    const openTime = bar.openTime ?? bar.timestamp

    if (openTime === undefined || !Number.isFinite(openTime)) {
      throw new PineExecutionError(`bars[${index}] must include a valid timestamp or openTime.`)
    }

    for (const [field, value] of Object.entries({
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
      volume: bar.volume,
    })) {
      if (!Number.isFinite(value)) {
        throw new PineExecutionError(`bars[${index}].${field} must be a finite number.`)
      }
    }

    return {
      openTime: toMilliseconds(openTime),
      ...(bar.closeTime === undefined ? {} : { closeTime: toMilliseconds(bar.closeTime) }),
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
      volume: bar.volume,
    }
  })

const asRecord = (value: unknown): Record<string, unknown> | undefined =>
  typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined

const asArray = (value: unknown): unknown[] => (Array.isArray(value) ? value : [])

const asFiniteNumber = (value: unknown): number | undefined =>
  typeof value === 'number' && Number.isFinite(value) ? value : undefined

const resolveCoordinate = (value: unknown, xloc: unknown, bars: PineBar[]) => {
  const coordinate = asFiniteNumber(value)
  if (coordinate === undefined) {
    return {}
  }

  if (xloc === 'bar_time') {
    return { timestamp: toMilliseconds(coordinate) }
  }

  const barIndex = Number.isInteger(coordinate) ? coordinate : undefined
  const timestamp = barIndex !== undefined ? bars[barIndex]?.openTime : undefined
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

  // PineTS currently emits a single drawing call site directly as
  // { title, option, data }, but uses a keyed map when call sites collide.
  const entries = 'data' in collection ? [[name, collection] as const] : Object.entries(collection)

  return entries.flatMap(([key, value]) => {
    const entry = asRecord(value) as PlotEntry | undefined
    return asArray(entry?.data).flatMap((sample) => {
      const sampleRecord = asRecord(sample)
      // Drawing plots are time-series containers. The actual LabelObject,
      // LineObject, or BoxObject instances live in sample.value.
      const drawingValues = sampleRecord && 'value' in sampleRecord
        ? asArray(sampleRecord.value)
        : [sample]

      return drawingValues.map((item) => ({ key, title: entry?.title, item }))
    })
  })
}

const normalizePlots = (plots: PinePlots) =>
  Object.entries(plots)
    .filter(([key]) => !key.startsWith('__'))
    .map(([key, value]) => {
      const entry = asRecord(value) as PlotEntry | undefined
      return {
        key,
        ...(typeof entry?.title === 'string' ? { title: entry.title } : {}),
        ...(entry?.option === undefined ? {} : { options: entry.option }),
        data: asArray(entry?.data),
      }
    })

const normalizeDrawings = (plots: PinePlots, bars: PineBar[]) => ({
  labels: collectDrawingData(plots, '__labels__').flatMap(({ key, title, item }, index) => {
    const label = asRecord(item)
    if (!label || label._deleted === true) {
      return []
    }

    return [{
      id: `${key}-${label.id ?? index}`,
      ...(typeof title === 'string' ? { title } : {}),
      ...resolveCoordinate(label.x, label.xloc, bars),
      ...(asFiniteNumber(label.y) === undefined ? {} : { price: label.y }),
      ...(typeof label.text === 'string' ? { text: label.text } : {}),
      ...(typeof label.style === 'string' ? { style: label.style } : {}),
      ...(typeof label.color === 'string' ? { color: label.color } : {}),
      ...(typeof label.textcolor === 'string' ? { textColor: label.textcolor } : {}),
    }]
  }),
  lines: collectDrawingData(plots, '__lines__').flatMap(({ key, title, item }, index) => {
    const line = asRecord(item)
    if (!line || line._deleted === true) {
      return []
    }

    return [{
      id: `${key}-${line.id ?? index}`,
      ...(typeof title === 'string' ? { title } : {}),
      start: {
        ...resolveCoordinate(line.x1, line.xloc, bars),
        ...(asFiniteNumber(line.y1) === undefined ? {} : { price: line.y1 }),
      },
      end: {
        ...resolveCoordinate(line.x2, line.xloc, bars),
        ...(asFiniteNumber(line.y2) === undefined ? {} : { price: line.y2 }),
      },
      ...(typeof line.extend === 'string' ? { extend: line.extend } : {}),
      ...(typeof line.style === 'string' ? { style: line.style } : {}),
      ...(typeof line.color === 'string' ? { color: line.color } : {}),
      ...(asFiniteNumber(line.width) === undefined ? {} : { width: line.width }),
    }]
  }),
  boxes: collectDrawingData(plots, '__boxes__').flatMap(({ key, title, item }, index) => {
    const box = asRecord(item)
    if (!box || box._deleted === true) {
      return []
    }

    return [{
      id: `${key}-${box.id ?? index}`,
      ...(typeof title === 'string' ? { title } : {}),
      start: resolveCoordinate(box.left, box.xloc, bars),
      end: resolveCoordinate(box.right, box.xloc, bars),
      ...(asFiniteNumber(box.top) === undefined ? {} : { top: box.top }),
      ...(asFiniteNumber(box.bottom) === undefined ? {} : { bottom: box.bottom }),
      ...(typeof box.extend === 'string' ? { extend: box.extend } : {}),
      ...(typeof box.border_color === 'string' ? { borderColor: box.border_color } : {}),
      ...(typeof box.border_style === 'string' ? { borderStyle: box.border_style } : {}),
      ...(asFiniteNumber(box.border_width) === undefined ? {} : { borderWidth: box.border_width }),
      ...(typeof box.bgcolor === 'string' ? { backgroundColor: box.bgcolor } : {}),
      ...(typeof box.text === 'string' ? { text: box.text } : {}),
    }]
  }),
})

export const executePineScript = async ({ source, bars }: ExecutePineRequest) => {
  if (typeof source !== 'string' || !source.trim()) {
    throw new PineExecutionError('source must not be empty.')
  }

  if (!Array.isArray(bars) || bars.length === 0) {
    throw new PineExecutionError('bars must contain at least one candle.')
  }

  try {
    const normalizedBars = normalizeBars(bars)
    const context = await new PineTS(normalizedBars).run(source)
    const rawPlots = asRecord(context.plots) ?? {}

    return {
      indicator: context.indicator,
      plots: normalizePlots(rawPlots),
      drawings: normalizeDrawings(rawPlots, normalizedBars),
      warnings: context.warnings,
    }
  } catch (error) {
    if (error instanceof PineExecutionError) {
      throw error
    }

    const message = error instanceof Error ? error.message : 'Unknown PineTS execution error.'
    throw new PineExecutionError(message, error)
  }
}
