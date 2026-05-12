import type { FutureOpportunityAnalysisItem } from '@/api/modules'

export const OPPORTUNITY_UNKNOWN_TEXT = '-'

export const formatOpportunityNumber = (value?: number | null) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return OPPORTUNITY_UNKNOWN_TEXT
  }
  return Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 4,
  })
}

export const formatOpportunityDirection = (value?: string | null) => {
  if (value === 'up') {
    return '上涨'
  }
  if (value === 'down') {
    return '下跌'
  }
  return OPPORTUNITY_UNKNOWN_TEXT
}

export const formatOpportunityOpenSide = (value?: string | null) => {
  if (value === 'long') {
    return '做多'
  }
  if (value === 'short') {
    return '做空'
  }
  return OPPORTUNITY_UNKNOWN_TEXT
}

export const formatOpportunitySegmentType = (value?: string | null) => {
  if (value === 'trend_push') {
    return '趋势推动段'
  }
  if (value === 'trend_pullback') {
    return '趋势回调段'
  }
  if (value === 'range_internal') {
    return '区间内部段'
  }
  return OPPORTUNITY_UNKNOWN_TEXT
}

export const formatOpportunityRangePosition = (value?: string | null) => {
  if (value === 'upper_third') {
    return '上1/3'
  }
  if (value === 'lower_third') {
    return '下1/3'
  }
  if (value === 'middle_third') {
    return '中1/3'
  }
  return OPPORTUNITY_UNKNOWN_TEXT
}

export const formatOpportunityPriceRange = (low?: number | null, high?: number | null) => {
  if (low === null || low === undefined || high === null || high === undefined) {
    return OPPORTUNITY_UNKNOWN_TEXT
  }
  return `${formatOpportunityNumber(low)} ~ ${formatOpportunityNumber(high)}`
}

export const formatOpportunityMode = (value?: string | null) => {
  if (value === 'mode_1') {
    return '模式一'
  }
  if (value === 'mode_2') {
    return '模式二'
  }
  if (value === 'mode_3') {
    return '模式三'
  }
  if (value === 'mode_4') {
    return '模式四'
  }
  return OPPORTUNITY_UNKNOWN_TEXT
}

export const opportunityModeTagType = (value?: string | null) => {
  if (value === 'mode_1') {
    return 'danger'
  }
  if (value === 'mode_2') {
    return 'success'
  }
  if (value === 'mode_3') {
    return 'warning'
  }
  if (value === 'mode_4') {
    return 'info'
  }
  return ''
}

export const formatOpportunityTradingRangeState = (row: FutureOpportunityAnalysisItem) => {
  const rangeText = formatOpportunityPriceRange(row.trading_range_bottom, row.trading_range_top)
  if (rangeText === OPPORTUNITY_UNKNOWN_TEXT) {
    return OPPORTUNITY_UNKNOWN_TEXT
  }
  const enteredText = row.is_in_30f_trading_range ? '已进入' : '未进入'
  const positionText = row.is_in_30f_trading_range
    ? ` / ${formatOpportunityRangePosition(row.trading_range_position)}`
    : ''
  return `${rangeText} / ${enteredText}${positionText}`
}

export const formatOpportunityMomentumState = (
  checkDirection?: string | null,
  exhausted?: boolean | null,
) => {
  if (!checkDirection || exhausted === null || exhausted === undefined) {
    return OPPORTUNITY_UNKNOWN_TEXT
  }
  const checkText = checkDirection === 'up' ? '检查上涨段' : '检查下跌段'
  const stateText = exhausted ? '已衰竭' : '未衰竭'
  return `${checkText} / ${stateText}`
}

export const formatOpportunityAction = (row: FutureOpportunityAnalysisItem) => {
  if (!row.has_opportunity || !row.opportunity_action) {
    return '没机会'
  }
  if (row.opportunity_action === 'open_long_wait_5f_down_end') {
    return '开多机会：等待5F下跌段结束'
  }
  if (row.opportunity_action === 'open_short_wait_5f_up_end') {
    return '开空机会：等待5F上涨段结束'
  }
  if (row.opportunity_action === 'open_long_follow_5f_up') {
    return '开多机会：顺5F上涨段参与'
  }
  if (row.opportunity_action === 'open_short_follow_5f_down') {
    return '开空机会：顺5F下跌段参与'
  }
  if (row.opportunity_action === 'open_long_reverse_5f_down_structure') {
    return '开多机会：逆5F下跌结构操作'
  }
  if (row.opportunity_action === 'open_short_reverse_5f_up_structure') {
    return '开空机会：逆5F上涨结构操作'
  }
  return '没机会'
}
