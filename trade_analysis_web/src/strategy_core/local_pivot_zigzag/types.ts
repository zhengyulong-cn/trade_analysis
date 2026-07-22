export type PineSeriesLike = {
  get: (offset: number) => number
}

export type PineJsLike = {
  Std: {
    close: (context: unknown) => number
    ema: (series: PineSeriesLike, length: number, context: unknown) => number
    high: (context: unknown) => number
    low: (context: unknown) => number
    open: (context: unknown) => number
  }
}

export type PineContextLike = {
  new_var: (value?: number) => PineSeriesLike
  setMinimumAdditionalDepth?: (depth: number) => void
}

export type PivotKind = 1 | -1

export type PivotPoint = {
  kind: PivotKind
  barIndex: number
  price: number
  zoneLower: number
  zoneUpper: number
}

export type PendingSegmentEnd = {
  colorIndex: number
  offset: number
  price: number
}

export type PendingZonePoint = {
  kind: PivotKind
  offset: number
  lower: number
  upper: number
}

export type StudyState = {
  barIndex: number
  bodyRanges: number[]
  lastLongPointIndex: number | null
  lastShortPointIndex: number | null
  pendingSegmentEnd: PendingSegmentEnd | null
  pendingZones: PendingZonePoint[]
  pivotPoints: PivotPoint[]
}