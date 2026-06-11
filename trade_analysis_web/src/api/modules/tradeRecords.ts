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
  color?: string
  text_color?: string
  border_color?: string
  tag_type?: "" | "success" | "info" | "warning" | "danger" | "primary"
  effect?: "dark" | "light" | "plain"
}

export interface TradeRecordColumn {
  column_id: number
  column_key: string
  column_label: string
  data_type: TradeRecordColumnDataType
  table_column_width: number | null
  option_source_type: TradeRecordColumnOptionSourceType
  is_required: boolean
  is_enabled: boolean
  sort_order: number
  options_json: TradeRecordColumnOption[]
  option_source_config: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface TradeRecordColumnCreateParams {
  column_key: string
  column_label: string
  data_type: TradeRecordColumnDataType
  table_column_width?: number | null
  option_source_type?: TradeRecordColumnOptionSourceType
  is_required?: boolean
  is_enabled?: boolean
  sort_order?: number
  options_json?: Array<Record<string, unknown>>
  option_source_config?: Record<string, unknown>
}

export interface TradeRecordColumnUpdateParams extends Partial<TradeRecordColumnCreateParams> {
  column_id: number
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

export interface TradeAccountCreateParams {
  account_name: string
  account_type: TradeAccountType
  account_no: string
  password: string
}

export interface TradeAccountUpdateParams extends Partial<TradeAccountCreateParams> {
  account_id: number
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

export const createTradeRecordColumnApi = (params: TradeRecordColumnCreateParams) => {
  return axios.post<TradeRecordColumn>("/trade-record-columns/create", params) as unknown as Promise<TradeRecordColumn>
}

export const updateTradeRecordColumnApi = (params: TradeRecordColumnUpdateParams) => {
  return axios.post<TradeRecordColumn>("/trade-record-columns/update", params) as unknown as Promise<TradeRecordColumn>
}

export const deleteTradeRecordColumnApi = (columnId: number) => {
  return axios.post<void>("/trade-record-columns/delete", { column_id: columnId }) as unknown as Promise<void>
}

export const getTradeAccountListApi = () => {
  return axios.get<TradeAccount[]>("/trade-accounts") as unknown as Promise<TradeAccount[]>
}

export const createTradeAccountApi = (params: TradeAccountCreateParams) => {
  return axios.post<TradeAccount>("/trade-accounts/create", params) as unknown as Promise<TradeAccount>
}

export const updateTradeAccountApi = (params: TradeAccountUpdateParams) => {
  return axios.post<TradeAccount>("/trade-accounts/update", params) as unknown as Promise<TradeAccount>
}

export const deleteTradeAccountApi = (accountId: number) => {
  return axios.post<void>("/trade-accounts/delete", { account_id: accountId }) as unknown as Promise<void>
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
