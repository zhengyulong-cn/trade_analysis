import axios from "@/api/axios";

export type TradeRecordSegmentType = "trend_push" | "trend_pullback" | "range_internal"
export type TradeRecordOpenDirection = "long" | "short"

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

export const getTradeRecordListApi = (params?: TradeRecordListParams) => {
  return axios.get<TradeRecord[]>("/trade-records", params) as unknown as Promise<TradeRecord[]>
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
