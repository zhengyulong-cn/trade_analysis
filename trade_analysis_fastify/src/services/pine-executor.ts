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

export const executePineScript = async ({ source, bars }: ExecutePineRequest) => {
  if (typeof source !== 'string' || !source.trim()) {
    throw new PineExecutionError('source must not be empty.')
  }

  if (!Array.isArray(bars) || bars.length === 0) {
    throw new PineExecutionError('bars must contain at least one candle.')
  }

  try {
    const context = await new PineTS(normalizeBars(bars)).run(source)

    return {
      indicator: context.indicator,
      plots: context.plots,
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
