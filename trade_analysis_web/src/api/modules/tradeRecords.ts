import axios from "@/api/axios";

export type TradeRecordSegmentType =
  | "trend_push"
  | "trend_pullback"
  | "range_internal"
  | "false_break_range_transition"
  | "true_break_trend_push_transition"
export type TradeRecordOpenSignal =
  | "ema20_resistance_key_level_confirmed"
  | "ema120_resistance_head_shoulders"
  | "ema120_resistance_three_push_wedge"
  | "ema120_resistance_range_break_pullback"
  | "range_edge_multiple_breakout_failures"
  | "real_breakout_with_engulfing"
  | "not_matching_open_signal"
export type TradeRecordOpenDirection = "long" | "short"
export type TradeRecordAnalysisPeriod = "day" | "week" | "half_month" | "month"
export type TradeRecordTag = "hold_and_hope" | "revenge_trade" | "correct_trade" | "close_late_profit_retreat" | "close_early_miss_opportunity" | "holiday_hold"

export interface TradeRecordScreenshot {
  path: string
  original_name: string
  content_type: string
  size: number
}

export interface TradeRecord {
  trade_record_id: number
  contract: string
  source: "manual" | "import"
  open_direction: TradeRecordOpenDirection
  lots: number
  open_time: string
  open_price: number | string
  close_time: string | null
  close_price: number | string | null
  segment_type: TradeRecordSegmentType | null
  open_signal: TradeRecordOpenSignal | null
  tags: TradeRecordTag[]
  fee: number | string
  actual_pnl: number | string | null
  screenshots: TradeRecordScreenshot[]
  comment: string | null
  created_at: string
  updated_at: string
}

export interface TradeRecordCreateParams {
  contract: string
  open_direction: TradeRecordOpenDirection
  lots: number
  open_time: string
  open_price: number
  close_time?: string | null
  close_price?: number | null
  segment_type: TradeRecordSegmentType
  open_signal?: TradeRecordOpenSignal | null
  tags?: TradeRecordTag[]
  fee: number
  actual_pnl?: number | null
  screenshots: TradeRecordScreenshot[]
  comment?: string | null
}

export interface TradeRecordUpdateParams extends Partial<TradeRecordCreateParams> {
  trade_record_id: number
}

export interface TradeRecordListParams {
  contract?: string
  open_direction?: TradeRecordOpenDirection
  segment_type?: TradeRecordSegmentType
  open_signal?: TradeRecordOpenSignal
  open_time_start?: string
  open_time_end?: string
  close_time_start?: string
  close_time_end?: string
}

export interface TradeRecordScreenshotUploadResult extends TradeRecordScreenshot {
  url: string
}

export interface TradeRecordImportResult {
  imported: number
  skipped: number
  failed: number
  message: string
}

export interface TradeRecordMergeParams {
  trade_record_ids: number[]
}

export interface TradeRecordAnalysisParams {
  period_type: TradeRecordAnalysisPeriod
  contract?: string
  open_direction?: TradeRecordOpenDirection
  segment_type?: TradeRecordSegmentType
  open_signal?: TradeRecordOpenSignal
  tags?: TradeRecordTag[]
  open_time_start?: string
  open_time_end?: string
}

export interface TradeRecordAnalysisSummary {
  trade_count: number
  total_lots: number
  gross_pnl: number | string
  total_fee: number | string
  net_pnl: number | string
  win_count: number
  loss_count: number
  win_rate: number | null
  avg_net_pnl: number | string | null
  trading_days: number
  avg_trades_per_day: number | null
  signal_coverage_rate: number | null
  invalid_signal_rate: number | null
}

export interface TradeRecordAnalysisPeriodItem {
  period_label: string
  period_start: string
  period_end: string
  trade_count: number
  total_lots: number
  gross_pnl: number | string
  total_fee: number | string
  net_pnl: number | string
  win_count: number
  loss_count: number
  win_rate: number | null
  avg_net_pnl: number | string | null
  empty_signal_count: number
  invalid_signal_count: number
  valid_signal_count: number
  signal_coverage_rate: number | null
  invalid_signal_rate: number | null
  cumulative_net_pnl: number | string
  net_pnl_change: number | string | null
  trade_count_change: number | null
  win_rate_change: number | null
  risk_flags: string[]
}

export interface TradeRecordAnalysisLossStreakItem {
  streak_length: number
  start_period_label: string
  end_period_label: string
  start_period_start: string
  end_period_end: string
  trade_count: number
  gross_pnl: number | string
  total_fee: number | string
  net_pnl: number | string
  win_count: number
  loss_count: number
  win_rate: number | null
}

export interface TradeRecordAnalysisBreakdownItem {
  key: string | null
  label: string
  trade_count: number
  total_lots: number
  gross_pnl: number | string
  total_fee: number | string
  net_pnl: number | string
  win_count: number
  loss_count: number
  win_rate: number | null
  avg_net_pnl: number | string | null
  signal_coverage_rate: number | null
  invalid_signal_rate: number | null
}

export interface TradeRecordAnalysisResult {
  summary: TradeRecordAnalysisSummary
  period_series: TradeRecordAnalysisPeriodItem[]
  by_contract: TradeRecordAnalysisBreakdownItem[]
  by_direction: TradeRecordAnalysisBreakdownItem[]
  by_segment_type: TradeRecordAnalysisBreakdownItem[]
  by_open_signal: TradeRecordAnalysisBreakdownItem[]
  continuous_loss_periods: TradeRecordAnalysisLossStreakItem[]
  high_frequency_periods: TradeRecordAnalysisPeriodItem[]
  execution_worse_periods: TradeRecordAnalysisPeriodItem[]
}

export const getTradeRecordListApi = (params?: TradeRecordListParams) => {
  return axios.get<TradeRecord[]>("/trade-records", params) as unknown as Promise<TradeRecord[]>
}

export const getTradeRecordAnalysisApi = (params: TradeRecordAnalysisParams) => {
  return axios.get<TradeRecordAnalysisResult>("/trade-records/analysis", params) as unknown as Promise<
    TradeRecordAnalysisResult
  >
}

export const createTradeRecordApi = (params: TradeRecordCreateParams) => {
  return axios.post<TradeRecord>("/trade-records/create", params) as unknown as Promise<TradeRecord>
}

export const updateTradeRecordApi = (params: TradeRecordUpdateParams) => {
  return axios.post<TradeRecord>("/trade-records/update", params) as unknown as Promise<TradeRecord>
}

export const deleteTradeRecordApi = (tradeRecordId: number) => {
  return axios.post<void>("/trade-records/delete", { trade_record_id: tradeRecordId }) as unknown as Promise<void>
}

export const mergeTradeRecordsApi = (params: TradeRecordMergeParams) => {
  return axios.post<TradeRecord>("/trade-records/merge", params) as unknown as Promise<TradeRecord>
}

export const uploadTradeRecordScreenshotApi = (file: File) => {
  const formData = new FormData()
  formData.append("file", file)
  return axios.post<TradeRecordScreenshotUploadResult>("/trade-records/upload-screenshot", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  }) as unknown as Promise<TradeRecordScreenshotUploadResult>
}

export const importTradeRecordsApi = (file: File) => {
  const formData = new FormData()
  formData.append("file", file)
  return axios.post<TradeRecordImportResult>("/trade-records/import", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  }) as unknown as Promise<TradeRecordImportResult>
}

export const resolveTradeRecordScreenshotUrl = (path?: string | null) => {
  if (!path) {
    return ""
  }

  if (/^https?:\/\//.test(path)) {
    return path
  }

  return `/storage/${path.replace(/^\/+/, "")}`
}
