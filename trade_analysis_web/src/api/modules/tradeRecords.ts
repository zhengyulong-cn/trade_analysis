import axios from "@/api/axios";

export type TradeRecordSegmentType =
  | "\u8d8b\u52bf\u63a8\u52a8\u6bb5"
  | "\u8d8b\u52bf\u56de\u8c03\u6bb5"
  | "\u533a\u95f4\u5185\u90e8\u6bb5"

export interface TradeRecord {
  trade_record_id: number
  contract: string
  lots: number
  open_time: string
  open_price: number | string
  close_time: string
  close_price: number | string
  segment_type: TradeRecordSegmentType
  actual_pnl: number | string
  screenshot_path: string | null
  screenshot_original_name: string | null
  screenshot_content_type: string | null
  screenshot_size: number | null
  comment: string | null
  created_at: string
  updated_at: string
}

export interface TradeRecordCreateParams {
  contract: string
  lots: number
  open_time: string
  open_price: number
  close_time: string
  close_price: number
  segment_type: TradeRecordSegmentType
  actual_pnl: number
  screenshot_path?: string | null
  screenshot_original_name?: string | null
  screenshot_content_type?: string | null
  screenshot_size?: number | null
  comment?: string | null
}

export interface TradeRecordUpdateParams extends Partial<TradeRecordCreateParams> {
  trade_record_id: number
  remove_screenshot?: boolean
}

export interface TradeRecordListParams {
  contract?: string
  segment_type?: TradeRecordSegmentType
  open_time_start?: string
  open_time_end?: string
  close_time_start?: string
  close_time_end?: string
}

export interface TradeRecordScreenshotUploadResult {
  path: string
  original_name: string
  content_type: string
  size: number
  url: string
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

export const resolveTradeRecordScreenshotUrl = (path?: string | null) => {
  if (!path) {
    return ""
  }

  if (/^https?:\/\//.test(path)) {
    return path
  }

  return `/storage/${path.replace(/^\/+/, "")}`
}
