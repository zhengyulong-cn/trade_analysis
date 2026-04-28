import axios from "@/api/axios";
import { toChartTimestampSeconds } from "@/utils/date";

export interface FutureContract {
  contract_id: number
  symbol: string
  exchange: string
  name: string
  is_favorite: number
  auto_load_segments: number
  create_at: string
  updated_at: string
}

export interface FutureContractCreateParams {
  symbol: string
  exchange: string
  name: string
  is_favorite?: number
  auto_load_segments?: number
}

export interface FutureContractUpdateParams extends Partial<FutureContractCreateParams> {
  contract_id: number
}

export interface FutureContractInterval {
  contract_interval_id: number
  contract_interval_name: string
  seconds: number
  description: string | null
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
  ema20?: number
  ema120?: number
  volume?: number
}

export interface FutureKlineQueryItem extends FutureKlineItem {
  symbol: string
  exchange: string
  contract_name: string
}

export interface FutureKlinePage {
  items: FutureKlineQueryItem[]
  total: number
  page: number
  page_size: number
}

export interface FutureKlineData {
  contract_id: number
  symbol: string
  exchange: string
  name: string
  kline_data: FutureKlineItem[]
  kLineList: FutureChartKLineItem[]
}

export interface FutureKlineSyncResult {
  symbol: string
  interval: number
  provider: string
  provider_symbol: string
  requested: number
  inserted: number
  updated: number
}

export interface FutureKlineDeleteResult {
  symbol: string
  interval: number
  deleted: number
}

export interface FutureKlineItemDeleteResult {
  kline_id: number
  deleted: number
}

export interface FutureStrategyAnalysisBuildParams {
  symbol: string
  interval: number
  reset?: boolean
}

export interface FutureStrategyEmaState {
  period: number
  seed_closes: Array<number | string>
  last_ema: number | string | null
  last_relation: string | null
  warmup_bars: FutureKlineItem[]
}

export interface FutureTrendSegment {
  segment_index: number
  direction: string
  status: string
  trigger_time: string
  first_kline_time: string
  last_kline_time: string
  start_time: string
  start_price: number | string
  end_time: string
  end_price: number | string
  kline_count: number
  confirmed_at: string | null
}

export interface FutureIntervalStrategy {
  interval: number
  interval_name: string | null
  ema_state: FutureStrategyEmaState
  confirmed_segments: FutureTrendSegment[]
  current_segment: FutureTrendSegment | null
  processed_kline_count: number
  last_processed_at: string | null
}

export interface FutureStrategyContent {
  intervals: Record<string, FutureIntervalStrategy>
}

export interface FutureStrategyAnalysisDetail {
  strategy_id: number
  contract_id: number
  symbol: string
  exchange: string
  contract_name: string
  strategy: FutureStrategyContent
}

export interface FutureSegmentBuildResult {
  strategy_id: number
  contract_id: number
  symbol: string
  exchange: string
  contract_name: string
  interval: number
  interval_name: string | null
  strategy: FutureStrategyContent
  interval_strategy: FutureIntervalStrategy
}

export type FutureStrategySegmentRole = 'confirmed' | 'current' | 'pending'

export interface FutureStrategySegmentItem {
  segment_role: FutureStrategySegmentRole
  segment_index: number
  direction: string
  status: string
  trigger_time: string
  first_kline_time: string
  last_kline_time: string
  start_time: string
  start_price: number | string
  end_time: string
  end_price: number | string
  kline_count: number
  bars_since_end: number
  confirmed_at: string | null
}

export interface FutureStrategySegmentListResult {
  strategy_id: number | null
  contract_id: number
  symbol: string
  exchange: string
  contract_name: string
  interval: number
  interval_name: string | null
  items: FutureStrategySegmentItem[]
}

export interface FutureStrategySegmentBaseParams {
  symbol: string
  interval: number
  segment_role: FutureStrategySegmentRole
  direction: string
  start_time: string
  start_price: number
  end_time: string
  end_price: number
}

export interface FutureStrategySegmentCreateParams extends FutureStrategySegmentBaseParams {}

export interface FutureStrategySegmentUpdateParams extends FutureStrategySegmentBaseParams {
  original_segment_role: FutureStrategySegmentRole
  original_segment_index: number
}

export interface FutureStrategySegmentDeleteItem {
  segment_role: FutureStrategySegmentRole
  segment_index: number
}

export interface FutureStrategySegmentBatchDeleteParams {
  symbol: string
  interval: number
  items: FutureStrategySegmentDeleteItem[]
}

export interface FutureStrategySegmentBatchDeleteResult {
  symbol: string
  interval: number
  deleted: number
  remaining: number
}

export interface FutureStrategyAnalysisDeleteParams {
  contract_id: number
  strategy_id: number
}

export interface FutureStrategyAnalysisDeleteResult {
  contract_id: number
  strategy_id: number
  deleted: number
}

export interface FutureChartPersistence {
  persistence_id: number | null
  user_key: string
  symbol: string
  interval: string
  drawings_content: string | null
  create_at: string | null
  updated_at: string | null
}

export interface FutureChartPersistenceSaveParams {
  symbol: string
  interval: string
  drawings_content?: string | null
}

export interface FutureRealtimeBar {
  symbol: string
  exchange: string
  interval: number
  bucket_start: string
  bucket_end: string
  date_time: string
  open: number | string
  high: number | string
  low: number | string
  close: number | string
  volume: number | string
  hold: number | string
  quote_volume: number | string
  quote_time: string
  provider: string | null
  provider_symbol: string | null
}

export interface FutureRealtimeBarResult {
  symbol: string
  interval: number
  bar: FutureRealtimeBar | null
}

const mapFutureKlineToChartData = (item: FutureKlineItem): FutureChartKLineItem | null => {
  const timestamp = toChartTimestampSeconds(item.date_time)
  if (timestamp === null) {
    return null
  }

  return {
    time: timestamp,
    open: Number(item.open),
    high: Number(item.high),
    low: Number(item.low),
    close: Number(item.close),
    volume: Number(item.volume),
  }
}

export const mapRealtimeBarToChartData = (bar: FutureRealtimeBar): FutureChartKLineItem | null => {
  const timestamp = toChartTimestampSeconds(bar.date_time)
  if (timestamp === null) {
    return null
  }

  return {
    time: timestamp,
    open: Number(bar.open),
    high: Number(bar.high),
    low: Number(bar.low),
    close: Number(bar.close),
    volume: Number(bar.volume),
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

export const getFutureContractIntervalList = () => {
  return axios.get<FutureContractInterval[]>("/contract-intervals/") as unknown as Promise<
    FutureContractInterval[]
  >
}

export const createFutureContract = (params: FutureContractCreateParams) => {
  return axios.post<FutureContract>("/contracts/create", params) as unknown as Promise<FutureContract>
}

export const updateFutureContract = (params: FutureContractUpdateParams) => {
  return axios.post<FutureContract>("/contracts/update", params) as unknown as Promise<FutureContract>
}

export const getFutureKlinePageApi = (params: {
  symbol: string
  interval: number
  page?: number
  page_size?: number
  start_time?: string
  end_time?: string
}) => {
  return axios.get<FutureKlinePage>("/klines/page", params) as unknown as Promise<FutureKlinePage>
}

export const syncFutureKlinesApi = (params: { symbol: string; interval: number }) => {
  return axios.post<FutureKlineSyncResult>("/klines/sync/market-data", params) as unknown as Promise<
    FutureKlineSyncResult
  >
}

export const deleteFutureKlinesApi = (params: { symbol: string; interval: number }) => {
  return axios.post<FutureKlineDeleteResult>("/klines/delete", params) as unknown as Promise<
    FutureKlineDeleteResult
  >
}

export const deleteFutureKlineItemApi = (params: { kline_id: number }) => {
  return axios.post<FutureKlineItemDeleteResult>("/klines/delete/item", params) as unknown as Promise<
    FutureKlineItemDeleteResult
  >
}

export const buildFutureSegmentAnalysisApi = (params: FutureStrategyAnalysisBuildParams) => {
  return axios.post<FutureSegmentBuildResult>("/strategy-analyses/segments/build", params) as unknown as Promise<
    FutureSegmentBuildResult
  >
}

export const getFutureStrategyAnalysisApi = (params: { symbol: string }) => {
  return axios.get<FutureStrategyAnalysisDetail>("/strategy-analyses", params) as unknown as Promise<
    FutureStrategyAnalysisDetail
  >
}

export const getFutureStrategySegmentListApi = (params: { symbol: string; interval: number }) => {
  return axios.get<FutureStrategySegmentListResult>("/strategy-analyses/segments", params) as unknown as Promise<
    FutureStrategySegmentListResult
  >
}

export const createFutureStrategySegmentApi = (params: FutureStrategySegmentCreateParams) => {
  return axios.post<FutureStrategySegmentListResult>("/strategy-analyses/segments/create", params) as unknown as Promise<
    FutureStrategySegmentListResult
  >
}

export const updateFutureStrategySegmentApi = (params: FutureStrategySegmentUpdateParams) => {
  return axios.post<FutureStrategySegmentListResult>("/strategy-analyses/segments/update", params) as unknown as Promise<
    FutureStrategySegmentListResult
  >
}

export const deleteFutureStrategySegmentsApi = (params: FutureStrategySegmentBatchDeleteParams) => {
  return axios.post<FutureStrategySegmentBatchDeleteResult>("/strategy-analyses/segments/delete", params) as unknown as Promise<
    FutureStrategySegmentBatchDeleteResult
  >
}

export const deleteFutureStrategyAnalysisApi = (params: FutureStrategyAnalysisDeleteParams) => {
  return axios.post<FutureStrategyAnalysisDeleteResult>("/strategy-analyses/delete", params) as unknown as Promise<
    FutureStrategyAnalysisDeleteResult
  >
}

export const getFutureChartPersistenceApi = (params: { symbol: string; interval: string }) => {
  return axios.get<FutureChartPersistence>("/chart-persistences", params) as unknown as Promise<
    FutureChartPersistence
  >
}

export const saveFutureChartPersistenceApi = (params: FutureChartPersistenceSaveParams) => {
  return axios.post<FutureChartPersistence>("/chart-persistences/save", params) as unknown as Promise<
    FutureChartPersistence
  >
}

export const getFutureRealtimeBarApi = (params: { symbol: string; interval: number }) => {
  return axios.get<FutureRealtimeBarResult>("/realtime-bars/current", params) as unknown as Promise<
    FutureRealtimeBarResult
  >
}
