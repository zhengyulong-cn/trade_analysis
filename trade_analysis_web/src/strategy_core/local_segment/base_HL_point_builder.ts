export type PineSeriesLike = {
  get: (offset: number) => number
}

const isConfirmedHigh = (
  highSeries: PineSeriesLike,
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

const isConfirmedLow = (
  lowSeries: PineSeriesLike,
  offsetBars: number,
) => {
  const candidate = lowSeries.get(offsetBars)
  for (let i = 2 * offsetBars; i >= 0; i--) {
    if (i === offsetBars) {
      continue
    }
    const comparedValue = lowSeries.get(i)
    if (comparedValue < candidate) {
      return false
    }
  }
  return true
}

export const buildBaseHLPoint = (
  highSeries: PineSeriesLike,
  lowSeries: PineSeriesLike,
  ema20Series: PineSeriesLike,
  offsetBars: number,
) => {
  const candidateHigh = highSeries.get(offsetBars)
  const candidateLow = lowSeries.get(offsetBars)
  const candidateEma20 = ema20Series.get(offsetBars)

  return {
    candidateHigh,
    candidateLow,
    candidateEma20,
    highPoint: isConfirmedHigh(highSeries, offsetBars) && candidateHigh > candidateEma20,
    lowPoint: isConfirmedLow(lowSeries, offsetBars) && candidateLow < candidateEma20,
  }
}
