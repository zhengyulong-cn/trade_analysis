import axios from "@/api/axios"

export type UploadScope = "trade_records_v2" | "opportunity_reviews"

export interface ImageAttachment {
  path: string
  original_name: string
  content_type: string
  size: number
}

export interface ImageUploadResult extends ImageAttachment {
  url: string
}

export const uploadImageApi = (file: File, scope: UploadScope) => {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("scope", scope)

  return axios.post<ImageUploadResult>("/uploads/image", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  }) as unknown as Promise<ImageUploadResult>
}

export const resolveStorageImageUrl = (path?: string | null) => {
  if (!path) {
    return ""
  }

  if (/^https?:\/\//.test(path)) {
    return path
  }

  return `/storage/${path.replace(/^\/+/, "")}`
}
