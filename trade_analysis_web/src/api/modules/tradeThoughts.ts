import axios from "@/api/axios";

export interface TradeThoughtImage {
  path: string
  original_name: string
  content_type: string
  size: number
}

export interface TradeThought {
  thought_id: number
  title: string | null
  categories: string | null
  content: string
  codes: string[]
  images: TradeThoughtImage[]
  created_at: string
  updated_at: string
}

export interface TradeThoughtCreateParams {
  title?: string | null
  categories?: string | null
  content: string
  codes?: string[]
  images?: TradeThoughtImage[]
}

export interface TradeThoughtUpdateParams extends Partial<TradeThoughtCreateParams> {
  thought_id: number
}

export interface TradeThoughtImageUploadResult extends TradeThoughtImage {
  url: string
}

export const getTradeThoughtListApi = () => {
  return axios.get<TradeThought[]>("/trade-thoughts") as unknown as Promise<TradeThought[]>
}

export const createTradeThoughtApi = (params: TradeThoughtCreateParams) => {
  return axios.post<TradeThought>("/trade-thoughts/create", params) as unknown as Promise<TradeThought>
}

export const updateTradeThoughtApi = (params: TradeThoughtUpdateParams) => {
  return axios.post<TradeThought>("/trade-thoughts/update", params) as unknown as Promise<TradeThought>
}

export const deleteTradeThoughtApi = (thoughtId: number) => {
  return axios.post<void>("/trade-thoughts/delete", { thought_id: thoughtId }) as unknown as Promise<void>
}

export const uploadTradeThoughtImageApi = (file: File) => {
  const formData = new FormData()
  formData.append("file", file)
  return axios.post<TradeThoughtImageUploadResult>("/trade-thoughts/upload-image", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  }) as unknown as Promise<TradeThoughtImageUploadResult>
}

export const resolveTradeThoughtImageUrl = (path?: string | null) => {
  if (!path) {
    return ""
  }

  if (/^https?:\/\//.test(path)) {
    return path
  }

  return `/storage/${path.replace(/^\/+/, "")}`
}
