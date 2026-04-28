export interface KLineItem {
  time: number
  open: number
  high: number
  low: number
  close: number
  ema20?: number
  ema120?: number
  volume?: number
}

export interface ContractOption {
  label: string
  value: string
  description?: string
  isFavorite?: boolean
}

export interface PeriodOption {
  label: string
  value: number | string
}

export interface TradingViewBar {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume?: number
}
