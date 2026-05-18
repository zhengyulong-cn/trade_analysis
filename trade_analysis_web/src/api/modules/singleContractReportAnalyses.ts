import axios from "@/api/axios";

export interface SingleContractReportAnalysisResult {
  relevance: "high" | "medium" | "low" | "none"
  stance: "bullish" | "bearish" | "neutral" | "mixed"
  horizon: string
  confidence: number
  summary: string
  drivers: string[]
  risks: string[]
  evidence: string[]
}

export interface SingleContractReportAnalysisListItem {
  analysis_id: number
  product_id: number
  report_id: number
  profile_id: number | null
  product_code: string
  product_name: string
  report_title: string
  report_source: string | null
  status: string
  error_message: string | null
  matched_snippets: string[]
  result_json: SingleContractReportAnalysisResult | null
  create_at: string
  updated_at: string
}

export interface SingleContractReportAnalysis extends SingleContractReportAnalysisListItem {
  profile_snapshot: {
    focus_dimensions?: string[]
    analysis_style?: string | null
    extra_instruction?: string | null
    output_preference?: string | null
    is_active?: number
  } | null
  system_prompt: string
  user_prompt: string
}

export interface SingleContractReportAnalysisRunPayload {
  product_id: number
  report_id: number
}

export const getSingleContractReportAnalysisListApi = (params?: {
  product_id?: number
  report_id?: number
}) => {
  return axios.get<SingleContractReportAnalysisListItem[]>(
    "/single-product-report-analyses",
    params,
  ) as unknown as Promise<SingleContractReportAnalysisListItem[]>
}

export const getSingleContractReportAnalysisItemApi = (analysisId: number) => {
  return axios.get<SingleContractReportAnalysis>(
    `/single-product-report-analyses/item/${analysisId}`,
  ) as unknown as Promise<SingleContractReportAnalysis>
}

export const runSingleContractReportAnalysisApi = (payload: SingleContractReportAnalysisRunPayload) => {
  return axios.post<SingleContractReportAnalysis>(
    "/single-product-report-analyses/run",
    payload,
  ) as unknown as Promise<SingleContractReportAnalysis>
}
