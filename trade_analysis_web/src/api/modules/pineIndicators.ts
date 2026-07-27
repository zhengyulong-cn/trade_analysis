import axios from "@/api/axios"

export interface PineIndicatorExecuteParams {
  script_id: number
  symbol: string
  interval: number
  limit?: number
}

export interface PineIndicatorExecuteResult {
  script_id: number
  script_name: string
  symbol: string
  interval: number
  bar_count: number
  indicator: Record<string, unknown>
  plots: Record<string, unknown>
  warnings: Array<Record<string, unknown>>
}

export const executePineIndicatorApi = (params: PineIndicatorExecuteParams) => {
  return axios.post<PineIndicatorExecuteResult>("/pine-indicators/execute", params) as unknown as Promise<PineIndicatorExecuteResult>
}
