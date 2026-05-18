import axios from "@/api/axios";

export interface FutureReportDocument {
  report_id: number
  report_name: string
  published_at: string
  report_source: string
  storage_path: string
  original_filename: string
  content_type: string
  file_size: number
  create_at: string
  updated_at: string
}

export interface FutureReportUploadResult extends FutureReportDocument {
  url: string
}

export interface FutureFundamentalAnalysis {
  analysis_id: number
  product_id: number
  report_id: number
  supply_side: string | null
  demand_side: string | null
  inventory_side: string | null
  industry_profit: string | null
  substitution_linkage: string | null
  policy_macro: string | null
  conclusion: string | null
  create_at: string
  updated_at: string
  product_code: string
  product_display_name: string
  report_name: string
  report_storage_path: string
}

export interface FutureFundamentalAnalysisCreateParams {
  product_id: number
  report_id: number
  supply_side?: string | null
  demand_side?: string | null
  inventory_side?: string | null
  industry_profit?: string | null
  substitution_linkage?: string | null
  policy_macro?: string | null
  conclusion?: string | null
}

export interface FutureFundamentalAnalysisUpdateParams
  extends Partial<FutureFundamentalAnalysisCreateParams> {
  analysis_id: number
}

export const getFutureReportDocumentListApi = () => {
  return axios.get<FutureReportDocument[]>("/future-report-documents") as unknown as Promise<FutureReportDocument[]>
}

export const uploadFutureReportDocumentApi = (params: {
  published_at: string
  report_source: string
  file: File
}) => {
  const formData = new FormData()
  formData.append("published_at", params.published_at)
  formData.append("report_source", params.report_source)
  formData.append("file", params.file)
  return axios.post<FutureReportUploadResult>("/future-report-documents/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  }) as unknown as Promise<FutureReportUploadResult>
}

export const deleteFutureReportDocumentApi = (reportId: number) => {
  return axios.post<void>("/future-report-documents/delete", { report_id: reportId }) as unknown as Promise<void>
}

export const getFutureFundamentalAnalysisListApi = () => {
  return axios.get<FutureFundamentalAnalysis[]>("/future-fundamental-analyses") as unknown as Promise<
    FutureFundamentalAnalysis[]
  >
}

export const createFutureFundamentalAnalysisApi = (params: FutureFundamentalAnalysisCreateParams) => {
  return axios.post("/future-fundamental-analyses/create", params) as unknown as Promise<void>
}

export const updateFutureFundamentalAnalysisApi = (params: FutureFundamentalAnalysisUpdateParams) => {
  return axios.post("/future-fundamental-analyses/update", params) as unknown as Promise<void>
}

export const deleteFutureFundamentalAnalysisApi = (analysisId: number) => {
  return axios.post<void>("/future-fundamental-analyses/delete", {
    analysis_id: analysisId,
  }) as unknown as Promise<void>
}

export const resolveFutureReportPdfUrl = (path?: string | null) => {
  if (!path) {
    return ""
  }
  if (/^https?:\/\//.test(path)) {
    return path
  }
  return `/storage/${path.replace(/^\/+/, "")}`
}
