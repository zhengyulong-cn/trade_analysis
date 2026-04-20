import axios from "@/api/axios";

export interface FutureContract {
  contract_id: number
  symbol: string
  exchange: string
  name: string
  create_at: string
  updated_at: string
}

export interface FutureContractCreateParams {
  symbol: string
  exchange: string
  name: string
}

export interface FutureContractUpdateParams extends Partial<FutureContractCreateParams> {
  contract_id: number
}

export const getFutureDataApi = (params: { symbol: string; period: number }) => {
  return axios.get("/klines", {
    symbol: params.symbol,
    interval: params.period,
  });
}

export const getFutureContractList = () => {
  return axios.get<FutureContract[]>("/contracts") as unknown as Promise<FutureContract[]>
}

export const createFutureContract = (params: FutureContractCreateParams) => {
  return axios.post<FutureContract>("/contracts/create", params) as unknown as Promise<FutureContract>
}

export const updateFutureContract = (params: FutureContractUpdateParams) => {
  return axios.post<FutureContract>("/contracts/update", params) as unknown as Promise<FutureContract>
}
