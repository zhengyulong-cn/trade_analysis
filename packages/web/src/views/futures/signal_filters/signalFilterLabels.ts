import type { FutureEmaTrendState } from '@/api/modules'

const EMA_TREND_STATE_LABELS: Record<FutureEmaTrendState, string> = {
  bull_trend: '多头单边',
  bull_expanding: '多头扩张',
  bull_contracting: '多头收缩',
  bear_trend: '空头单边',
  bear_expanding: '空头扩张',
  bear_contracting: '空头收缩',
  neutral: '震荡',
}

export const formatEmaTrendState = (state: FutureEmaTrendState) => EMA_TREND_STATE_LABELS[state]
