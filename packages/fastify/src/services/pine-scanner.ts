import type { PineAlert } from '@trade-analysis/core'

import {
  executePineScript,
  type ExecutePineRequest,
  type PineInputBar,
} from './pine-executor.js'

export const SCAN_SIGNAL_TITLE = 'SCAN_SIGNAL'

export type PineScanContract = {
  symbol: string
  exchange: string
  name: string
  bars: PineInputBar[]
}

export type ExecutePineScanRequest = {
  source: string
  contracts: PineScanContract[]
  signalTitle?: string
}

export type PineScanMatch = {
  symbol: string
  exchange: string
  name: string
  message: string
  triggeredAt: number
}

const findLatestSignal = (
  alerts: PineAlert[],
  barCount: number,
  signalTitle: string,
) => alerts
  .filter((alert) => (
    alert.type === 'alertcondition'
    && alert.title === signalTitle
    && alert.barIndex === barCount - 1
  ))
  .sort((first, second) => (second.timestamp ?? 0) - (first.timestamp ?? 0))[0]

export const executePineScanner = async ({
  source,
  contracts,
  signalTitle = SCAN_SIGNAL_TITLE,
}: ExecutePineScanRequest) => {
  const matches: PineScanMatch[] = []

  for (const contract of contracts) {
    const execution: ExecutePineRequest = { source, bars: contract.bars }
    const result = await executePineScript(execution)
    const signal = findLatestSignal(result.alerts, contract.bars.length, signalTitle)
    if (!signal) {
      continue
    }

    matches.push({
      symbol: contract.symbol,
      exchange: contract.exchange,
      name: contract.name,
      message: signal.message ?? '',
      triggeredAt: signal.timestamp ?? contract.bars.at(-1)?.closeTime ?? contract.bars.at(-1)?.timestamp ?? 0,
    })
  }

  return { scannedCount: contracts.length, matches }
}
