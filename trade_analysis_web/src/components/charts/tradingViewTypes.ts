export interface TradingViewSubscription<TArgs extends unknown[]> {
  subscribe: (context: object | null, handler: (...args: TArgs) => void, singleshot?: boolean) => void
  unsubscribe: (context: object | null, handler: (...args: TArgs) => void) => void
}

export interface TradingViewActiveChart {
  crossHairMoved: () => TradingViewSubscription<[{
    time?: number
  }]>
  onDataLoaded: () => TradingViewSubscription<[]>
  onSymbolChanged: () => TradingViewSubscription<[{
    name: string
    ticker?: string
  }]>
  onIntervalChanged: () => TradingViewSubscription<[string, Record<string, unknown>]>
  createStudyTemplate?: (options?: { saveSymbol?: boolean; saveInterval?: boolean }) => object
  getAllStudies?: () => Array<{
    id?: string | number
    name?: string
  }>
  createStudy?: (
    name: string,
    forceOverlay?: boolean,
    lock?: boolean,
    inputs?: Record<string, unknown> | unknown[],
  ) => Promise<unknown> | unknown
  applyStudyTemplate?: (template: object) => void
  getLineToolsState?: () => TradingViewLineToolsAndGroupsState
  applyLineToolsState?: (state: TradingViewLineToolsAndGroupsState) => Promise<void>
  setVisibleRange: (range: { from: number; to: number }, options?: Record<string, unknown>) => Promise<void>
  resetData?: () => void
}

export interface TradingViewWidget {
  onChartReady: (callback: () => void) => void
  subscribe: (event: string, callback: () => void) => void
  unsubscribe: (event: string, callback: () => void) => void
  activeChart: () => TradingViewActiveChart
  resetCache?: () => void
  remove: () => void
}

export interface TradingViewLineToolsAndGroupsState {
  sources: Map<string, unknown | null> | null
  groups: Map<string, unknown | null>
  symbol?: string
}

export type TradingViewConstructor = new (options: Record<string, unknown>) => TradingViewWidget

declare global {
  interface Window {
    TradingView?: {
      widget: TradingViewConstructor
    }
  }
}

export {}
