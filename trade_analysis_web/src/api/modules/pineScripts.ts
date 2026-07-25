import axios from "@/api/axios";

export type PineScriptType = "indicator" | "strategy" | "scanner"

export interface PineScript {
  script_id: number
  script_name: string
  script_content: string
  script_type: PineScriptType
  created_at: string
  updated_at: string
}

export interface PineScriptCreateParams {
  script_name: string
  script_content: string
  script_type: PineScriptType
}

export interface PineScriptUpdateParams extends Partial<PineScriptCreateParams> {
  script_id: number
}

export const getPineScriptListApi = () => {
  return axios.get<PineScript[]>("/pine-scripts") as unknown as Promise<PineScript[]>
}

export const createPineScriptApi = (params: PineScriptCreateParams) => {
  return axios.post<PineScript>("/pine-scripts/create", params) as unknown as Promise<PineScript>
}

export const updatePineScriptApi = (params: PineScriptUpdateParams) => {
  return axios.post<PineScript>("/pine-scripts/update", params) as unknown as Promise<PineScript>
}

export const deletePineScriptApi = (scriptId: number) => {
  return axios.post<void>("/pine-scripts/delete", { script_id: scriptId }) as unknown as Promise<void>
}
