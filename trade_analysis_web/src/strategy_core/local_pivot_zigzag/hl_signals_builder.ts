import type { PineSeriesLike, PivotKind, StudyState } from "./types"

const isFiniteNumber = (value: unknown): value is number => (
  typeof value === 'number' && Number.isFinite(value)
)

// export const isConfirmedHigh = (
//   highSeries: PineSeriesLike,
//   ema20Series: PineSeriesLike,
//   offsetBars: number,
// ) => {
//   const candidate = highSeries.get(offsetBars)
//   const candidateEma20 = ema20Series.get(offsetBars)
//   if (!isFiniteNumber(candidate) || !isFiniteNumber(candidateEma20) || candidate <= candidateEma20) {
//     return false
//   }

//   for (let offset = 0; offset <= offsetBars * 2; offset += 1) {
//     if (offset === offsetBars) {
//       continue
//     }
//     const comparedValue = highSeries.get(offset)
//     if (!isFiniteNumber(comparedValue) || comparedValue > candidate) {
//       return false
//     }
//   }
//   return true
// }

export const isConfirmedHigh = (
  highSeries: PineSeriesLike,
  ema20Series: PineSeriesLike,
  offsetBars: number,
) => {
  const candidate = highSeries.get(offsetBars)
  for (let i = 2 * offsetBars; i >= 0; i--) {
    if (i === offsetBars) {
      continue
    }
    const comparedValue = highSeries.get(i)
    if (comparedValue > candidate) {
      return false
    }
  }
  return true
}

export const isConfirmedLow = (
  lowSeries: PineSeriesLike,
  ema20Series: PineSeriesLike,
  offsetBars: number,
) => {
  const candidate = lowSeries.get(offsetBars)
  const candidateEma20 = ema20Series.get(offsetBars)
  if (!isFiniteNumber(candidate) || !isFiniteNumber(candidateEma20) || candidate >= candidateEma20) {
    return false
  }

  for (let offset = 0; offset <= offsetBars * 2; offset += 1) {
    if (offset === offsetBars) {
      continue
    }
    const comparedValue = lowSeries.get(offset)
    if (!isFiniteNumber(comparedValue) || comparedValue < candidate) {
      return false
    }
  }
  return true
}

export const processPivot = (
  state: StudyState,
  kind: PivotKind,
  barIndex: number,
  price: number,
  center: number,
  tolerance: number,
  requiredDistance: number,
) => {
  const lastPoint = state.pivotPoints[state.pivotPoints.length - 1]
  const point = {
    kind,
    barIndex,
    price,
    zoneLower: center - tolerance,
    zoneUpper: center + tolerance,
  }

  if (!lastPoint) {
    state.pivotPoints.push(point)
    return { added: point, previous: null, replaced: false }
  }

  if (lastPoint.kind === kind) {
    const isMoreExtreme = kind === 1 ? price > lastPoint.price : price < lastPoint.price
    if (isMoreExtreme) {
      Object.assign(lastPoint, point)
      return { added: null, previous: null, replaced: true }
    }
    return { added: null, previous: null, replaced: false }
  }

  const previousPoint = state.pivotPoints[state.pivotPoints.length - 2]
  const isPreviousDownSegmentBroken = (
    kind === 1
    && lastPoint.kind === -1
    && previousPoint?.kind === 1
    && price > previousPoint.price
  )
  if (isPreviousDownSegmentBroken) {
    state.pivotPoints.push(point)
    return { added: point, previous: lastPoint, replaced: false }
  }

  if (barIndex - lastPoint.barIndex > requiredDistance) {
    state.pivotPoints.push(point)
    return { added: point, previous: lastPoint, replaced: false }
  }

  return { added: null, previous: null, replaced: false }
}
