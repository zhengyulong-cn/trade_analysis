import axios from "@/api/axios"

export type OpportunityReviewColumnDataType =
  | "bool"
  | "string"
  | "number"
  | "datetime"
  | "single_select"
  | "multi_select"
  | "images"

export interface OpportunityReviewColumnOption {
  label: string
  value: string
  color?: string
  text_color?: string
  border_color?: string
  tag_type?: "" | "success" | "info" | "warning" | "danger" | "primary"
  effect?: "dark" | "light" | "plain"
}

export interface OpportunityReviewColumn {
  column_id: number
  column_key: string
  column_label: string
  data_type: OpportunityReviewColumnDataType
  table_column_width: number | null
  is_required: boolean
  is_enabled: boolean
  sort_order: number
  options_json: OpportunityReviewColumnOption[]
  created_at: string
  updated_at: string
}

export interface OpportunityReviewColumnCreateParams {
  column_key: string
  column_label: string
  data_type: OpportunityReviewColumnDataType
  table_column_width?: number | null
  is_required?: boolean
  is_enabled?: boolean
  sort_order?: number
  options_json?: Array<Record<string, unknown>>
}

export interface OpportunityReviewColumnUpdateParams extends Partial<OpportunityReviewColumnCreateParams> {
  column_id: number
}

export interface OpportunityReview {
  opportunity_review_id: number
  data_json: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface OpportunityReviewCreateParams {
  data_json: Record<string, unknown>
}

export interface OpportunityReviewUpdateParams {
  opportunity_review_id: number
  data_json: Record<string, unknown>
}

export const getOpportunityReviewColumnListApi = () => {
  return axios.get<OpportunityReviewColumn[]>("/opportunity-review-columns") as unknown as Promise<OpportunityReviewColumn[]>
}

export const createOpportunityReviewColumnApi = (params: OpportunityReviewColumnCreateParams) => {
  return axios.post<OpportunityReviewColumn>("/opportunity-review-columns/create", params) as unknown as Promise<OpportunityReviewColumn>
}

export const updateOpportunityReviewColumnApi = (params: OpportunityReviewColumnUpdateParams) => {
  return axios.post<OpportunityReviewColumn>("/opportunity-review-columns/update", params) as unknown as Promise<OpportunityReviewColumn>
}

export const deleteOpportunityReviewColumnApi = (columnId: number) => {
  return axios.post<void>("/opportunity-review-columns/delete", { column_id: columnId }) as unknown as Promise<void>
}

export const getOpportunityReviewListApi = () => {
  return axios.get<OpportunityReview[]>("/opportunity-reviews") as unknown as Promise<OpportunityReview[]>
}

export const createOpportunityReviewApi = (params: OpportunityReviewCreateParams) => {
  return axios.post<OpportunityReview>("/opportunity-reviews/create", params) as unknown as Promise<OpportunityReview>
}

export const updateOpportunityReviewApi = (params: OpportunityReviewUpdateParams) => {
  return axios.post<OpportunityReview>("/opportunity-reviews/update", params) as unknown as Promise<OpportunityReview>
}

export const deleteOpportunityReviewApi = (opportunityReviewId: number) => {
  return axios.post<void>("/opportunity-reviews/delete", { opportunity_review_id: opportunityReviewId }) as unknown as Promise<void>
}
