import type {
  TradeRecordOpenDirection,
  TradeRecordOpenSignal,
  TradeRecordSegmentType,
  TradeRecordTag,
} from '@/api/modules'
import type { TagProps } from 'element-plus'

export const SEGMENT_PUSH: TradeRecordSegmentType = 'trend_push'
export const OPEN_DIRECTION_LONG: TradeRecordOpenDirection = 'long'

export const segmentTypeOptions: Array<{ label: string; value: TradeRecordSegmentType }> = [
  { label: '趋势推动段', value: 'trend_push' },
  { label: '趋势回调段', value: 'trend_pullback' },
  { label: '区间内部段', value: 'range_internal' },
  { label: '假突破转区间段', value: 'false_break_range_transition' },
  { label: '真突破区间转推动段', value: 'true_break_trend_push_transition' },
]

export const segmentTypeLabelMap: Record<TradeRecordSegmentType, string> = {
  trend_push: '趋势推动段',
  trend_pullback: '趋势回调段',
  range_internal: '区间内部段',
  false_break_range_transition: '假突破转区间段',
  true_break_trend_push_transition: '真突破区间转推动段',
}

export const openSignalOptions: Array<{ label: string; value: TradeRecordOpenSignal }> = [
  { label: 'EMA20阻力+站稳关键位', value: 'ema20_resistance_key_level_confirmed' },
  { label: 'EMA120阻力+头肩顶/头肩底', value: 'ema120_resistance_head_shoulders' },
  { label: 'EMA120阻力+三推楔形', value: 'ema120_resistance_three_push_wedge' },
  { label: 'EMA120阻力+突破交易区间然后回拉', value: 'ema120_resistance_range_break_pullback' },
  { label: '区间上下轨附近+两次以上尝试突破受阻', value: 'range_edge_multiple_breakout_failures' },
  { label: '不符合开仓信号', value: 'not_matching_open_signal' },
]

export const openSignalLabelMap: Record<TradeRecordOpenSignal, string> = {
  ema20_resistance_key_level_confirmed: 'EMA20阻力+站稳关键位',
  ema120_resistance_head_shoulders: 'EMA120阻力+头肩顶/头肩底',
  ema120_resistance_three_push_wedge: 'EMA120阻力+三推楔形',
  ema120_resistance_range_break_pullback: 'EMA120阻力+突破交易区间然后回拉',
  range_edge_multiple_breakout_failures: '区间上下轨附近+两次以上尝试突破受阻',
  not_matching_open_signal: '不符合开仓信号',
}

export const openDirectionOptions: Array<{ label: string; value: TradeRecordOpenDirection }> = [
  { label: '多单', value: 'long' },
  { label: '空单', value: 'short' },
]

export const openDirectionLabelMap: Record<TradeRecordOpenDirection, string> = {
  long: '多单',
  short: '空单',
}

export const tagOptions: Array<{ label: string; value: TradeRecordTag }> = [
  { label: '扛单', value: 'hold_and_hope' },
  { label: '报复性开仓', value: 'revenge_trade' },
  { label: '完美操作', value: 'perfect_trade' },
  { label: '利润较大回吐', value: 'large_profit_giveback' },
  { label: '节假日持仓', value: 'holiday_hold' },
]

export interface TradeRecordTagMeta {
  label: string
  type: TagProps['type']
}

export const tagLabelMap: Record<TradeRecordTag, TradeRecordTagMeta> = {
  hold_and_hope: {
    label: '扛单',
    type: 'danger',
  },
  revenge_trade: {
    label: '报复性开仓',
    type: 'danger',
  },
  perfect_trade: {
    label: '完美操作',
    type: 'success',
  },
  large_profit_giveback: {
    label: '利润较大回吐',
    type: 'warning',
  },
  holiday_hold: {
    label: '节假日持仓',
    type: 'danger'
  }
}
