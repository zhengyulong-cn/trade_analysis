import axios from "@/api/axios";

export interface ReportDocumentListItem {
  report_id: number
  file_name: string
  original_name: string
  content_type: string
  file_size: number
  title: string | null
  published_at: string | null
  source: string | null
  parse_status: string
  create_at: string
  updated_at: string
}

export interface ReportDocument extends ReportDocumentListItem {
  storage_path: string
  raw_text: string
}

export interface UploadReportDocumentPayload {
  published_at: string
  source: string
  file: File
}

export const getReportDocumentListApi = () => {
  return axios.get<ReportDocumentListItem[]>("/report-documents") as unknown as Promise<ReportDocumentListItem[]>
}

export const getReportDocumentItemApi = (reportId: number) => {
  return axios.get<ReportDocument>(`/report-documents/item/${reportId}`) as unknown as Promise<ReportDocument>
}

export const uploadReportDocumentApi = (payload: UploadReportDocumentPayload) => {
  const formData = new FormData()
  formData.append("published_at", payload.published_at)
  formData.append("source", payload.source)
  formData.append("file", payload.file)
  return axios.post<ReportDocument>("/report-documents/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  }) as unknown as Promise<ReportDocument>
}

export const deleteReportDocumentApi = (reportId: number) => {
  return axios.post<void>("/report-documents/delete", { report_id: reportId }) as unknown as Promise<void>
}
