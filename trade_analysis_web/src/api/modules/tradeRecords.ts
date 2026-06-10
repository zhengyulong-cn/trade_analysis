import axios from "@/api/axios"

export type TradeRecordColumnDataType =
  | "bool"
  | "string"
  | "number"
  | "datetime"
  | "single_select"
  | "multi_select"
  | "images"

export type TradeRecordColumnOptionSourceType = "static" | "outer"
export type TradeAccountType = "real" | "simulated"

export interface TradeRecordColumnOption {
  label: string
  value: string
}

export interface TradeRecordColumn {
  column_id: number
  column_key: string
  column_label: string
  data_type: TradeRecordColumnDataType
  option_source_type: TradeRecordColumnOptionSourceType
  is_required: boolean
  is_enabled: boolean
  sort_order: number
  options_json: TradeRecordColumnOption[]
  option_source_config: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface TradeAccount {
  account_id: number
  account_name: string
  account_type: TradeAccountType
  account_no: string
  password: string
  created_at: string
  updated_at: string
}

export interface TradeRecordImage {
  path: string
  original_name: string
  content_type: string
  size: number
}

export interface TradeRecordImageUploadResult extends TradeRecordImage {
  url: string
}

export interface TradeRecord {
  trade_record_id: number
  data_json: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface TradeRecordCreateParams {
  data_json: Record<string, unknown>
}

export interface TradeRecordUpdateParams {
  trade_record_id: number
  data_json: Record<string, unknown>
}

export const getTradeRecordColumnListApi = () => {
  return axios.get<TradeRecordColumn[]>("/trade-record-columns") as unknown as Promise<TradeRecordColumn[]>
}

export const getTradeAccountListApi = () => {
  return axios.get<TradeAccount[]>("/trade-accounts") as unknown as Promise<TradeAccount[]>
}

export const getTradeRecordListApi = () => {
  return axios.get<TradeRecord[]>("/trade-records") as unknown as Promise<TradeRecord[]>
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

export const uploadTradeRecordImageApi = (file: File) => {
  const formData = new FormData()
  formData.append("file", file)
  return axios.post<TradeRecordImageUploadResult>("/trade-records/upload-image", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  }) as unknown as Promise<TradeRecordImageUploadResult>
}

export const resolveTradeRecordImageUrl = (path?: string | null) => {
  if (!path) {
    return ""
  }

  if (/^https?:\/\//.test(path)) {
    return path
  }

  return `/storage/${path.replace(/^\/+/, "")}`
}
