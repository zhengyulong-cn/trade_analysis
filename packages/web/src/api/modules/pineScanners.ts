import axios from "@/api/axios"

export interface PineScannerExecuteParams {
  script_id: number
  interval: number
  limit?: number
}

export interface PineScannerMatch {
  contract_id: number
  symbol: string
  exchange: string
  name: string
  message: string
  triggered_at: string
}

export interface PineScannerExecuteResult {
  script_id: number
  script_name: string
  interval: number
  contract_count: number
  scanned_count: number
  matches: PineScannerMatch[]
}

export const executePineScannerApi = (params: PineScannerExecuteParams) => (
  axios.post<PineScannerExecuteResult>("/pine-scanners/execute", params) as unknown as Promise<PineScannerExecuteResult>
)
