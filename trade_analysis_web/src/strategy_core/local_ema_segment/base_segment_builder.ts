import type {
  BaseSegment,
  BaseSegmentBuildState,
  EmaSegmentBar,
  SegmentDirection,
  SegmentPoint,
  UpsertBarResult,
} from './types'

export const isFiniteNumber = (value: number | undefined): value is number => (
  Number.isFinite(value) && !Number.isNaN(value)
)

export const createEmptyBaseSegmentBuildState = (): BaseSegmentBuildState => ({
  activeBaseSegment: null,
  historicalBaseSegments: [],
  processedBarCount: 0,
  seedDirection: null,
  seedExtreme: null,
})

/**
 * 将 charting_library 逐根推送过来的 K 线写入缓存。
 *
 * 大多数时候数据是按时间 append 的；但图表库也可能重算最后一根 K 线，
 * 或补历史 K 线，所以这里会按 time 做替换、插入和重新编号。
 */
export const upsertBar = (bars: EmaSegmentBar[], bar: Omit<EmaSegmentBar, 'index'>): UpsertBarResult => {
  const lastBar = bars[bars.length - 1]

  if (!lastBar || bar.time > lastBar.time) {
    bars.push({
      ...bar,
      index: bars.length,
    })
    return {
      index: bars.length - 1,
      type: 'append',
    }
  }

  if (bar.time === lastBar.time) {
    bars[bars.length - 1] = {
      ...bar,
      index: lastBar.index,
    }
    return {
      index: lastBar.index,
      type: 'replace_last',
    }
  }

  const existingIndex = bars.findIndex((item) => item.time === bar.time)
  if (existingIndex >= 0) {
    bars[existingIndex] = {
      ...bar,
      index: existingIndex,
    }
    return {
      index: existingIndex,
      type: 'replace_existing',
    }
  }

  bars.push({
    ...bar,
    index: bars.length,
  })
  bars.sort((first, second) => first.time - second.time)
  bars.forEach((item, index) => {
    item.index = index
  })

  return {
    index: bars.findIndex((item) => item.time === bar.time),
    type: 'insert_historical',
  }
}

export const getBaseSegmentExtreme = (bar: EmaSegmentBar, direction: SegmentDirection): SegmentPoint => ({
  index: bar.index,
  price: direction === 'up' ? bar.high : bar.low,
  time: bar.time,
})

export const getBaseSegmentHighPoint = (baseSegment: BaseSegment): SegmentPoint => (
  baseSegment.direction === 'up' ? baseSegment.end : baseSegment.start
)

export const getBaseSegmentLowPoint = (baseSegment: BaseSegment): SegmentPoint => (
  baseSegment.direction === 'up' ? baseSegment.start : baseSegment.end
)

/** 克隆线段，避免外部读取后误改 buildState 中的活动对象。 */
const cloneBaseSegment = (baseSegment: BaseSegment): BaseSegment => ({
  direction: baseSegment.direction,
  end: { ...baseSegment.end },
  start: { ...baseSegment.start },
})

const createBaseSegment = (
  direction: SegmentDirection,
  start: SegmentPoint,
  end: SegmentPoint,
): BaseSegment => ({
  direction,
  start: { ...start },
  end: { ...end },
})

const updateActiveBaseSegmentEnd = (baseSegment: BaseSegment, end: SegmentPoint) => {
  baseSegment.end = { ...end }
}

/**
 * 判断新构筑段是否击穿了上一段起点。
 *
 * 例如当前尝试构筑下跌段，如果 K 线最高价突破上一上涨段起点，
 * 说明下跌段构筑失败，需要允许立即反向形成上涨段。
 */
const hasStartBreakReversal = (
  direction: SegmentDirection,
  reversalStartPoint: SegmentPoint | null,
  bar: EmaSegmentBar,
) => {
  if (!reversalStartPoint) {
    return false
  }

  if (direction === 'up') {
    return bar.high > reversalStartPoint.price
  }

  return bar.low < reversalStartPoint.price
}

/**
 * 尝试从 referencePoint 到当前 K 线构造一条新线段。
 *
 * 普通切段要求：
 * - 与 referencePoint 至少间隔 minSegmentBars 根 K 线；
 * - 上涨段需要 high 上穿 EMA，下跌段需要 low 下穿 EMA；
 * - 区间内不能出现比候选终点更极端的点，也不能击穿起点。
 *
 * 特殊切段：
 * - 如果当前 K 线击穿上一段起点，则忽略 minSegmentBars 和 EMA 穿越条件，
 *   直接允许反向构筑，用来处理“刚形成的新段失败”的回溯场景。
 */
const createPotentialBaseSegment = (
  direction: SegmentDirection,
  referencePoint: SegmentPoint,
  reversalStartPoint: SegmentPoint | null,
  bars: EmaSegmentBar[],
  bar: EmaSegmentBar,
  minSegmentBars: number,
): BaseSegment | null => {
  const startBreakReversal = hasStartBreakReversal(direction, reversalStartPoint, bar)

  if (!startBreakReversal && bar.index - referencePoint.index < minSegmentBars) {
    return null
  }

  if (direction === 'up') {
    if (!startBreakReversal && (!isFiniteNumber(bar.ema) || bar.high <= bar.ema)) {
      return null
    }

    const candidateEnd = getBaseSegmentExtreme(bar, 'up')

    for (let index = referencePoint.index + 1; index <= bar.index; index += 1) {
      const candidateBar = bars[index]
      if (!candidateBar) {
        continue
      }

      if (candidateBar.high > candidateEnd.price || candidateBar.low < referencePoint.price) {
        return null
      }
    }

    return createBaseSegment('up', referencePoint, candidateEnd)
  }

  if (!startBreakReversal && (!isFiniteNumber(bar.ema) || bar.low >= bar.ema)) {
    return null
  }

  const candidateEnd = getBaseSegmentExtreme(bar, 'down')

  for (let index = referencePoint.index + 1; index <= bar.index; index += 1) {
    const candidateBar = bars[index]
    if (!candidateBar) {
      continue
    }

    if (candidateBar.low < candidateEnd.price || candidateBar.high > referencePoint.price) {
      return null
    }
  }

  return createBaseSegment('down', referencePoint, candidateEnd)
}

/**
 * 处理还没有可绘制线段前的种子状态。
 *
 * 第一根有效 EMA K 线只用来确定一个不可见参考段：
 * close < EMA 视作前面是下跌参考段，记录最低点；
 * close > EMA 视作前面是上涨参考段，记录最高点。
 * 后续满足切段条件后，才生成第一条真正可绘制的 activeBaseSegment。
 */
const processSeedState = (
  buildState: BaseSegmentBuildState,
  bars: EmaSegmentBar[],
  bar: EmaSegmentBar,
  minSegmentBars: number,
) => {
  if (buildState.seedDirection === null || buildState.seedExtreme === null) {
    if (bar.close < bar.ema) {
      buildState.seedDirection = 'down'
      buildState.seedExtreme = getBaseSegmentExtreme(bar, 'down')
    } else if (bar.close > bar.ema) {
      buildState.seedDirection = 'up'
      buildState.seedExtreme = getBaseSegmentExtreme(bar, 'up')
    }
    return
  }

  if (buildState.seedDirection === 'down') {
    if (bar.low < buildState.seedExtreme.price) {
      buildState.seedExtreme = getBaseSegmentExtreme(bar, 'down')
      return
    }

    const nextActiveBaseSegment = createPotentialBaseSegment('up', buildState.seedExtreme, null, bars, bar, minSegmentBars)
    if (nextActiveBaseSegment) {
      buildState.activeBaseSegment = nextActiveBaseSegment
      buildState.seedDirection = null
      buildState.seedExtreme = null
    }
    return
  }

  if (bar.high > buildState.seedExtreme.price) {
    buildState.seedExtreme = getBaseSegmentExtreme(bar, 'up')
    return
  }

  const nextActiveBaseSegment = createPotentialBaseSegment('down', buildState.seedExtreme, null, bars, bar, minSegmentBars)
  if (nextActiveBaseSegment) {
    buildState.activeBaseSegment = nextActiveBaseSegment
    buildState.seedDirection = null
    buildState.seedExtreme = null
  }
}

/**
 * 处理当前正在构筑/绘制的线段。
 *
 * 同向刷新极值时只移动 activeBaseSegment.end；
 * 反向满足条件时，当前 activeBaseSegment 进入 historicalBaseSegments，
 * 新段成为 activeBaseSegment。
 */
const processActiveBaseSegment = (
  buildState: BaseSegmentBuildState,
  bars: EmaSegmentBar[],
  bar: EmaSegmentBar,
  minSegmentBars: number,
) => {
  const activeBaseSegment = buildState.activeBaseSegment
  if (!activeBaseSegment) {
    return
  }

  if (activeBaseSegment.direction === 'down') {
    if (bar.low < activeBaseSegment.end.price) {
      updateActiveBaseSegmentEnd(activeBaseSegment, getBaseSegmentExtreme(bar, 'down'))
      return
    }

    const nextActiveBaseSegment = createPotentialBaseSegment(
      'up',
      activeBaseSegment.end,
      activeBaseSegment.start,
      bars,
      bar,
      minSegmentBars,
    )
    if (nextActiveBaseSegment) {
      buildState.historicalBaseSegments.push(cloneBaseSegment(activeBaseSegment))
      buildState.activeBaseSegment = nextActiveBaseSegment
    }
    return
  }

  if (bar.high > activeBaseSegment.end.price) {
    updateActiveBaseSegmentEnd(activeBaseSegment, getBaseSegmentExtreme(bar, 'up'))
    return
  }

  const nextActiveBaseSegment = createPotentialBaseSegment(
    'down',
    activeBaseSegment.end,
    activeBaseSegment.start,
    bars,
    bar,
    minSegmentBars,
  )
  if (nextActiveBaseSegment) {
    buildState.historicalBaseSegments.push(cloneBaseSegment(activeBaseSegment))
    buildState.activeBaseSegment = nextActiveBaseSegment
  }
}

/**
 * 处理单根 K 线。
 *
 * EMA 未形成前不参与计算；形成后先走 seed 状态，
 * 一旦有 activeBaseSegment，后续都按 active 状态推进。
 */
const processBaseSegmentBar = (
  buildState: BaseSegmentBuildState,
  bars: EmaSegmentBar[],
  bar: EmaSegmentBar,
  emaLength: number,
  minSegmentBars: number,
) => {
  if (bar.index + 1 < emaLength || !isFiniteNumber(bar.ema)) {
    return
  }

  if (buildState.activeBaseSegment) {
    processActiveBaseSegment(buildState, bars, bar, minSegmentBars)
    return
  }

  processSeedState(buildState, bars, bar, minSegmentBars)
}

/** 增量推进到指定 barIndex，供需要精确单步推进的场景使用。 */
export const advanceBaseSegmentStateByIndex = (
  buildState: BaseSegmentBuildState,
  bars: EmaSegmentBar[],
  barIndex: number,
  emaLength: number,
  minSegmentBars: number,
) => {
  const bar = bars[barIndex]
  if (!bar) {
    return getAllBaseSegments(buildState)
  }

  processBaseSegmentBar(buildState, bars, bar, emaLength, minSegmentBars)
  buildState.processedBarCount = Math.max(buildState.processedBarCount, barIndex + 1)
  return getAllBaseSegments(buildState)
}

/** 从 buildState.processedBarCount 开始，把尚未处理的 K 线全部推进完。 */
export const advanceBaseSegmentState = (
  buildState: BaseSegmentBuildState,
  bars: EmaSegmentBar[],
  emaLength: number,
  minSegmentBars: number,
) => {
  for (let index = buildState.processedBarCount; index < bars.length; index += 1) {
    advanceBaseSegmentStateByIndex(buildState, bars, index, emaLength, minSegmentBars)
  }

  buildState.processedBarCount = bars.length
  return getAllBaseSegments(buildState)
}

/** 当参数变化、历史 K 线插入或缓存不一致时，从头重建线段状态。 */
export const rebuildBaseSegmentState = (
  bars: EmaSegmentBar[],
  emaLength: number,
  minSegmentBars: number,
) => {
  const buildState = createEmptyBaseSegmentBuildState()
  advanceBaseSegmentState(buildState, bars, emaLength, minSegmentBars)
  return buildState
}

/** 返回历史线段和当前活动线段；活动线段会克隆后返回，避免外部修改状态。 */
export const getAllBaseSegments = (buildState: BaseSegmentBuildState) => {
  if (!buildState.activeBaseSegment) {
    return [...buildState.historicalBaseSegments]
  }

  return [...buildState.historicalBaseSegments, cloneBaseSegment(buildState.activeBaseSegment)]
}

/** 图上只需要最新可绘制线段：优先返回活动段，没有活动段则返回最后一条历史段。 */
export const getLatestDrawableBaseSegment = (buildState: BaseSegmentBuildState) => {
  if (buildState.activeBaseSegment) {
    return buildState.activeBaseSegment
  }

  return buildState.historicalBaseSegments[buildState.historicalBaseSegments.length - 1] ?? null
}

export const buildBaseSegments = (bars: EmaSegmentBar[], emaLength: number, minSegmentBars: number) => {
  return getAllBaseSegments(rebuildBaseSegmentState(bars, emaLength, minSegmentBars))
}

export const getBaseSegmentKey = (baseSegment: BaseSegment) => {
  return `${baseSegment.start.time}-${baseSegment.direction}`
}

/** charting_library 的 dataoffset 是相对当前最后一根 K 线的位置偏移。 */
export const getOffsetFromCurrentBar = (bars: EmaSegmentBar[], point: SegmentPoint) => {
  const lastBar = bars[bars.length - 1]
  if (!lastBar) {
    return 0
  }

  return point.index - lastBar.index
}
