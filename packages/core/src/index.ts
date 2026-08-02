export interface PineBar {
  timestamp: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export const isPineBar = (value: unknown): value is PineBar => {
  if (typeof value !== "object" || value === null) {
    return false
  }

  const bar = value as Record<string, unknown>
  return ["timestamp", "open", "high", "low", "close", "volume"].every(
    (field) => typeof bar[field] === "number" && Number.isFinite(bar[field]),
  )
}
