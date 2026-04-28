import type { TradingViewWidget } from '@/components/charts/tradingViewTypes'
import { localAtrStrategy } from '@/strategy_core/local_atr'
import { localBollStrategy } from '@/strategy_core/local_boll'

const LOCAL_BOLL_STUDY_LENGTH = 20
const LOCAL_BOLL_STUDY_STD_DEV = 2
const LOCAL_ATR_STUDY_LENGTH = 14

export const addDefaultCustomStudies = (currentWidget: TradingViewWidget) => {
  const activeChart = currentWidget.activeChart()
  const existingStudies = activeChart.getAllStudies?.() ?? []
  const hasLocalBoll = existingStudies.some((study) => study.name === localBollStrategy.getLocalBollIndicatorName())
  const hasLocalAtr = existingStudies.some((study) => study.name === localAtrStrategy.getLocalAtrIndicatorName())

  const createStudy = activeChart.createStudy
  if (!createStudy) {
    return
  }

  try {
    if (!hasLocalBoll) {
      void createStudy.call(
        activeChart,
        localBollStrategy.getLocalBollIndicatorName(),
        false,
        false,
        {
          length: LOCAL_BOLL_STUDY_LENGTH,
          mult: LOCAL_BOLL_STUDY_STD_DEV,
        },
      )
    }

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
  } catch (error) {
    console.warn('Failed to create local custom studies', error)
  }
}

export const getCustomIndicators = async (PineJS: unknown) => {
  const indicatorGroups = await Promise.all([
    localBollStrategy.getCustomIndicators(PineJS as Parameters<typeof localBollStrategy.getCustomIndicators>[0]),
    localAtrStrategy.getCustomIndicators(PineJS as Parameters<typeof localAtrStrategy.getCustomIndicators>[0]),
  ])

  return indicatorGroups.flat()
}

export const getWhitelistedStudyTools = () => {
  return [
    { name: 'EMA Cross' },
    { name: 'MACD' },
    { name: localBollStrategy.getLocalBollIndicatorName() },
    { name: localAtrStrategy.getLocalAtrIndicatorName() },
  ]
}
