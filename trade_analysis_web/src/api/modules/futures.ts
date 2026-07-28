import axios from "@/api/axios";
import { toChartTimestampSeconds } from "@/utils/date";

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

export interface Watchlist {
  watchlist_id: number
  name: string
  display_order: number
  item_count: number
  create_at: string
  updated_at: string
}

export interface WatchlistContract extends FutureContract {
  display_order: number
}

export interface FutureMainContractCandidate {
  symbol: string
  exchange: string
  provider_symbol: string
  name: string
}

export interface FutureMainContractSyncParams {
  items: Array<{
    symbol: string
    exchange: string
    name: string
  }>
}

export interface FutureMainContractSyncResult {
  created: number
  updated: number
  items: FutureContract[]
}

export interface FutureKlineItem {
  kline_id: number
  contract_id: number
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

export interface FutureKlineItemsDeleteResult {
  requested: number
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

export const getFutureDataApi = async (params: { symbol: string; period: number; limit?: number }) => {
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
      limit: params.limit,
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

export const getWatchlistsApi = () => {
  return axios.get<Watchlist[]>('/watchlists') as unknown as Promise<Watchlist[]>
}

export const createWatchlistApi = (params: { name: string }) => {
  return axios.post<Watchlist>('/watchlists', params) as unknown as Promise<Watchlist>
}

export const deleteWatchlistApi = (watchlistId: number) => {
  return axios.post<void>(`/watchlists/${watchlistId}/delete`) as unknown as Promise<void>
}

export const getWatchlistContractsApi = (watchlistId: number) => {
  return axios.get<WatchlistContract[]>(`/watchlists/${watchlistId}/contracts`) as unknown as Promise<WatchlistContract[]>
}

export const addWatchlistContractApi = (watchlistId: number, contractId: number) => {
  return axios.post<void>(`/watchlists/${watchlistId}/contracts`, { contract_id: contractId }) as unknown as Promise<void>
}

export const removeWatchlistContractApi = (watchlistId: number, contractId: number) => {
  return axios.post<void>(`/watchlists/${watchlistId}/contracts/remove`, { contract_id: contractId }) as unknown as Promise<void>
}

export const reorderWatchlistContractsApi = (watchlistId: number, contractIds: number[]) => {
  return axios.post<void>(`/watchlists/${watchlistId}/contracts/reorder`, { contract_ids: contractIds }) as unknown as Promise<void>
}

export type FutureSignalDirection = 'all' | 'long' | 'short'

export interface FutureSignalFilterItem {
  signal_type: Exclude<FutureSignalDirection, 'all'>
  date_time: string
  open: number
  close: number
  high: number
  low: number
  ema20: number
  diff: number
  dea: number
  macd: number
  boundary: number
  within_boundary: boolean
}

export interface FutureSignalFilterResult {
  symbol: string
  exchange: string
  name: string
  interval: number
  bar_count: number
  signal_count: number
  signals: FutureSignalFilterItem[]
}

export interface FutureAdxRisingSignalItem {
  date_time: string
  open: number
  close: number
  high: number
  low: number
  tr: number
  di_plus: number
  di_minus: number
  dx: number
  adx: number
  previous_adx: number
  threshold: number
  above_threshold: boolean
  adx_slope: 'positive' | 'negative' | 'zero'
}

export type FutureEmaTrendState =
  | 'bull_trend'
  | 'bull_expanding'
  | 'bull_contracting'
  | 'bear_trend'
  | 'bear_expanding'
  | 'bear_contracting'
  | 'neutral'

export interface FutureEmaTrendSignalItem {
  date_time: string
  ema20: number
  ema120: number
  atr20: number
  gap_strength: number
  gap_change: number
  state: FutureEmaTrendState
}

export interface FutureHoldingWarningSignalItem {
  position_direction: 'long' | 'short'
  macd_signal_type: 'long' | 'short'
  date_time: string
  close: number
  ema_trend_state: FutureEmaTrendState
}

export interface FutureAdxRisingSignalResult {
  symbol: string
  exchange: string
  name: string
  interval: number
  period: number
  threshold: number
  bar_count: number
  signal_count: number
  signals: FutureAdxRisingSignalItem[]
}

export interface FutureContractSignalResult {
  symbol: string
  exchange: string
  name: string
  interval: number
  bar_count: number
  macd_signals: FutureSignalFilterItem[]
  adx_signals: FutureAdxRisingSignalItem[]
  ema_trend_signals: FutureEmaTrendSignalItem[]
  entry_signals: Array<{
    signal_type: 'long' | 'short'
    date_time: string
    open: number
    close: number
    high: number
    low: number
    adx_signal_date_time: string
    adx: number
    above_threshold: boolean
    ema20: number
    ema120: number
    gap_strength: number
    ema_trend_state: FutureEmaTrendState
  }>
  holding_warning_signals: FutureHoldingWarningSignalItem[]
}

export interface FutureAllContractSignalResult {
  interval: number
  contract_count: number
  items: FutureContractSignalResult[]
  entry_signals: Array<FutureContractSignalResult['entry_signals'][number] & {
    symbol: string
    exchange: string
    name: string
    interval: number
  }>
  holding_warning_signals: Array<FutureHoldingWarningSignalItem & {
    symbol: string
    exchange: string
    name: string
    interval: number
  }>
}

export const getFutureSignalsApi = (params: { symbol: string; interval: number; limit?: number }) => {
  return axios.get<FutureContractSignalResult>('/signal-filters/item', params) as unknown as Promise<FutureContractSignalResult>
}

export const getAllFutureSignalsApi = (params: { interval: number; limit?: number }) => {
  return axios.get<FutureAllContractSignalResult>('/signal-filters/all', params) as unknown as Promise<FutureAllContractSignalResult>
}

export const createFutureContract = (params: FutureContractCreateParams) => {
  return axios.post<FutureContract>("/contracts/create", params) as unknown as Promise<FutureContract>
}

export const updateFutureContract = (params: FutureContractUpdateParams) => {
  return axios.post<FutureContract>("/contracts/update", params) as unknown as Promise<FutureContract>
}

export const getFutureMainContracts = (params?: { has_night?: boolean }) => {
  return axios.get<FutureMainContractCandidate[]>("/contracts/main-contracts", params) as unknown as Promise<
    FutureMainContractCandidate[]
  >
}

export const syncFutureMainContracts = (params: FutureMainContractSyncParams) => {
  return axios.post<FutureMainContractSyncResult>("/contracts/main-contracts/sync", params) as unknown as Promise<
    FutureMainContractSyncResult
  >
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

export const syncFutureKlinesApi = (params: { symbol: string; interval: number; limit?: number }) => {
  return axios.post<FutureKlineSyncResult>("/klines/sync/market-data", params) as unknown as Promise<
    FutureKlineSyncResult
  >
}

export const deleteFutureKlinesApi = (params: { symbol: string; interval: number }) => {
  return axios.post<FutureKlineDeleteResult>("/klines/delete", params) as unknown as Promise<
    FutureKlineDeleteResult
  >
}

export const deleteFutureKlineItemsApi = (params: { kline_ids: number[] }) => {
  return axios.post<FutureKlineItemsDeleteResult>("/klines/delete/items", params) as unknown as Promise<
    FutureKlineItemsDeleteResult
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

