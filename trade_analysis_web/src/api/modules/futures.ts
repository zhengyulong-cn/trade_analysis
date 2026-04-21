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

export interface FutureKlineItem {
  kline_id: number
  contract_id: number
  interval_id: number
  interval: number
  open: number | string
  close: number | string
  high: number | string
  low: number | string
  volume: number | string
  hold: number | string
  date_time: string
}

export interface FutureChartKLineItem {
  time: number
  open: number
  high: number
  low: number
  close: number
}

export interface FutureKlineData {
  contract_id: number
  symbol: string
  exchange: string
  name: string
  kline_data: FutureKlineItem[]
  kLineList: FutureChartKLineItem[]
}

const mapFutureKlineToChartData = (item: FutureKlineItem): FutureChartKLineItem | null => {
  const timestamp = Math.floor(new Date(item.date_time).getTime() / 1000)
  if (Number.isNaN(timestamp)) {
    return null
  }

  return {
    time: timestamp,
    open: Number(item.open),
    high: Number(item.high),
    low: Number(item.low),
    close: Number(item.close),
  }
}

export const getFutureDataApi = async (params: { symbol: string; period: number }) => {
  const response = await (
    axios.get<{
      contract_id: number
      symbol: string
      exchange: string
      name: string
      kline_data: FutureKlineItem[]
    }>("/klines", {
      symbol: params.symbol,
      interval: params.period,
    }) as unknown as Promise<{
      contract_id: number
      symbol: string
      exchange: string
      name: string
      kline_data: FutureKlineItem[]
    }>
  )

  return {
    ...response,
    kLineList: response.kline_data
      .map(mapFutureKlineToChartData)
      .filter((item): item is FutureChartKLineItem => item !== null),
  } as FutureKlineData
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
