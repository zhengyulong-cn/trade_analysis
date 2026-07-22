import type { TradingViewWidget } from '@/components/charts/tradingViewTypes'
import { localAtrStrategy } from '@/strategy_core/local_atr'
import { localFenxinSegmentStrategy } from '@/strategy_core/local_fenxing_segment'
import { localPivotZigZagStrategy } from '@/strategy_core/local_pivot_zigzag'
import { localSegmentStrategy } from '@/strategy_core/local_segment'

const LOCAL_ATR_STUDY_LENGTH = 14

export const addLocalSegmentStudy = (currentWidget: TradingViewWidget) => {
  const activeChart = currentWidget.activeChart()
  const existingStudies = activeChart.getAllStudies?.() ?? []
  const hasLocalSegment = existingStudies.some(
    (study) => study.name === localSegmentStrategy.getLocalSegmentIndicatorName(),
  )
  const createStudy = activeChart.createStudy

  if (!createStudy || hasLocalSegment) {
    return
  }

  try {
    void createStudy.call(
      activeChart,
      localSegmentStrategy.getLocalSegmentIndicatorName(),
      true,
      false,
    )
  } catch (error) {
    console.warn('Failed to create local segment study', error)
  }
}

export const addDefaultCustomStudies = (currentWidget: TradingViewWidget) => {
  const activeChart = currentWidget.activeChart()
  const existingStudies = activeChart.getAllStudies?.() ?? []
  const hasLocalAtr = existingStudies.some((study) => study.name === localAtrStrategy.getLocalAtrIndicatorName())
  const hasLocalFenxinSegment = existingStudies.some(
    (study) => study.name === localFenxinSegmentStrategy.getLocalFenxinSegmentIndicatorName(),
  )
  const hasLocalPivotZigZag = existingStudies.some(
    (study) => study.name === localPivotZigZagStrategy.getLocalPivotZigZagIndicatorName(),
  )

  const createStudy = activeChart.createStudy
  if (!createStudy) {
    return
  }

  try {
    if (!hasLocalAtr) {
      void createStudy.call(
        activeChart,
        localAtrStrategy.getLocalAtrIndicatorName(),
        false,
        false,
        {
          length: LOCAL_ATR_STUDY_LENGTH,
        },
      )
    }

    if (!hasLocalFenxinSegment) {
      void createStudy.call(
        activeChart,
        localFenxinSegmentStrategy.getLocalFenxinSegmentIndicatorName(),
        true,
        false,
      )
    }

    if (!hasLocalPivotZigZag) {
      void createStudy.call(
        activeChart,
        localPivotZigZagStrategy.getLocalPivotZigZagIndicatorName(),
        true,
        false,
      )
    }
  } catch (error) {
    console.warn('Failed to create local custom studies', error)
  }
}

export const getCustomIndicators = async (PineJS: unknown) => {
  const indicatorGroups = await Promise.all([
    localAtrStrategy.getCustomIndicators(PineJS as Parameters<typeof localAtrStrategy.getCustomIndicators>[0]),
    localFenxinSegmentStrategy.getCustomIndicators(PineJS as Parameters<typeof localFenxinSegmentStrategy.getCustomIndicators>[0]),
    localPivotZigZagStrategy.getCustomIndicators(PineJS as Parameters<typeof localPivotZigZagStrategy.getCustomIndicators>[0]),
    localSegmentStrategy.getCustomIndicators(PineJS as Parameters<typeof localSegmentStrategy.getCustomIndicators>[0]),
  ])

  return indicatorGroups.flat()
}

export const getWhitelistedStudyTools = () => {
  return [
    { name: 'EMA Cross' },
    { name: 'MACD' },
    { name: localAtrStrategy.getLocalAtrIndicatorName() },
    { name: localFenxinSegmentStrategy.getLocalFenxinSegmentIndicatorName() },
    { name: localPivotZigZagStrategy.getLocalPivotZigZagIndicatorName() },
    { name: localSegmentStrategy.getLocalSegmentIndicatorName() },
  ]
}
