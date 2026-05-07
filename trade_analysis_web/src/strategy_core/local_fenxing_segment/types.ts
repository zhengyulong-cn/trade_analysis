/** TradingView study 运行时会传进来的 PineJS 能力子集。 */
export type PineJsLike = {
  Std: {
    close: (context: unknown) => number
    ema: (source: unknown, length: number, context: unknown) => number
    high: (context: unknown) => number
    low: (context: unknown) => number
    open: (context: unknown) => number
    time: (context: unknown) => number
  }
}

/** TradingView study 的上下文对象，当前主要用来取序列变量和最后一根 K 线状态。 */
export type PineContextLike = {
  new_var: (value?: number) => {
    get: (offset: number) => number
  }
  symbol?: {
    isLastBar?: boolean
  }
}

export type FenxingType = 'top' | 'bottom'

/** 原始 K 线。分型、线段、大级别线段、交易区间都基于它做增量推进。 */
export type FenxingBar = {
  close: number
  ema20: number
  ema120?: number
  high: number
  index: number
  low: number
  open: number
  time: number
}

/**
 * 包含处理后的 K 线。
 * 这里最重要的是 high/low 以及它们对应的原始 K 线位置；
 * open/close 对当前分型和线段逻辑不是必须的，因此没有保留。
 */
export type MergedFenxingBar = {
  firstBarCloseBelowEma20: boolean
  high: number
  highSourceIndex: number
  highSourceTime: number
  index: number
  low: number
  lowSourceIndex: number
  lowSourceTime: number
  sourceEndIndex: number
  sourceEndTime: number
  sourceStartIndex: number
  sourceStartTime: number
  time: number
}

/** 图形最终落点，统一使用原始 K 线索引和时间。 */
export type FenxingPoint = {
  index: number
  price: number
  time: number
}

/** 已确认分型信号，会作为本级别线段的输入。 */
export type FenxingSignal = {
  index: number
  mergedBarIndex: number
  point: FenxingPoint
  sourceEndIndex: number
  sourceEndTime: number
  sourceStartIndex: number
  sourceStartTime: number
  type: FenxingType
}

/** 分型构建状态：包含处理后的 K 线、已确认分型、以及已推进到的原始 K 线位置。 */
export type FenxingBuildState = {
  confirmedFenxingSignals: FenxingSignal[]
  mergedBars: MergedFenxingBar[]
  processedBarCount: number
}

/** 原始 K 线增量写入结果，用于决定是继续推进还是截断后重算。 */
export type UpsertFenxingBarResult = {
  index: number
  type: 'append' | 'insert_historical' | 'replace_existing' | 'replace_last'
}

export type SegmentDirection = 'up' | 'down'

/** 本级别线段，起止点都落在分型极值对应的原始 K 线上。 */
export type BaseSegment = {
  direction: SegmentDirection
  end: FenxingPoint
  endFenxingSignalIndex: number
  start: FenxingPoint
  startFenxingSignalIndex: number
}

/** 本级别线段状态：可能还在种子阶段，也可能已经有活动段。 */
export type BaseSegmentBuildState = {
  activeBaseSegment: BaseSegment | null
  historicalBaseSegments: BaseSegment[]
  processedFenxingSignalCount: number
  seedBottomFenxingSignal: FenxingSignal | null
  seedTopFenxingSignal: FenxingSignal | null
}

/** 大级别线段目前直接由本级别线段 + EMA20/EMA120 关系构建。 */
export type HigherLevelSegment = {
  direction: SegmentDirection
  end: FenxingPoint
  start: FenxingPoint
}

/** 大级别线段状态。lastCross* 用来记住最近一次 EMA20/EMA120 周期切换位置。 */
export type HigherLevelSegmentBuildState = {
  activeHigherLevelSegment: HigherLevelSegment | null
  historicalHigherLevelSegments: HigherLevelSegment[]
  lastCrossBarIndex: number | null
  lastCrossRelation: 'above' | 'below' | null
  processedBarCount: number
}

/** 交易区间中的特征序列元素，本质上是“方向受大级别约束”的本级别线段。 */
export type TradingRangeFeatureSegment = {
  baseSegmentIndex: number
  higherDirection: SegmentDirection
  segment: BaseSegment
}

/** 交易区间最终用于绘制矩形，上下边界来自特征序列重叠区间。 */
export type TradingRange = {
  bottom: number
  features: TradingRangeFeatureSegment[]
  left: FenxingPoint
  right: FenxingPoint
  top: number
}

/** 交易区间状态：活动区间、历史区间、最近特征段以及图形刷新标记。 */
export type TradingRangeBuildState = {
  activeTradingRange: TradingRange | null
  historicalTradingRanges: TradingRange[]
  lastFeatureSegment: TradingRangeFeatureSegment | null
  pendingGraphicsRefresh: boolean
  processedBaseSegmentCount: number
}

/** 线段强度度量：价差越大、跨越 K 线越短，说明力度越强。 */
export type BaseSegmentMetrics = {
  barSpan: number
  high: FenxingPoint
  low: FenxingPoint
  priceRange: number
  strength: number
}

/** 动能衰竭信号，当前仅保存方向、落点以及参与比较的力度信息。 */
export type MomentumExhaustionSignal = {
  direction: SegmentDirection
  point: FenxingPoint
  previousStrength: number
  currentStrength: number
}
