import {
  getFutureChartPersistenceApi,
  saveFutureChartPersistenceApi,
  type FutureChartPersistence,
  type FutureChartPersistenceSaveParams,
} from '@/api/modules'
import type { TradingViewLineToolsAndGroupsState, TradingViewWidget } from '@/components/charts/tradingViewTypes'

export type { FutureChartPersistence }

export const LOCAL_STUDY_TEMPLATE_KEY = 'trade-analysis:charting-library:study-template'

const MAP_SERIALIZATION_TYPE = '__tradingViewMap'

const isRecord = (value: unknown): value is Record<string, unknown> => {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

const isMapLike = (value: unknown): value is Map<unknown, unknown> => {
  return (
    Object.prototype.toString.call(value) === '[object Map]'
    && typeof (value as Map<unknown, unknown>).entries === 'function'
  )
}

export const stringifyChartJson = (value: unknown) => {
  try {
    return JSON.stringify(value, (_key, item) => {
      if (isMapLike(item)) {
        return {
          type: MAP_SERIALIZATION_TYPE,
          entries: Array.from(item.entries()),
        }
      }

      return item
    })
  } catch (error) {
    console.warn('Failed to stringify chart persistence content', error)
    return null
  }
}

export const parseChartJson = <T,>(content?: string | null): T | null => {
  if (!content) {
    return null
  }

  try {
    return JSON.parse(content, (_key, item) => {
      if (
        isRecord(item)
        && item.type === MAP_SERIALIZATION_TYPE
        && Array.isArray(item.entries)
      ) {
        return new Map(item.entries as Array<[unknown, unknown]>)
      }

      return item
    }) as T
  } catch (error) {
    console.warn('Failed to parse chart persistence content', error)
    return null
  }
}

export const loadChartPersistence = async (symbol: string, interval: string) => {
  try {
    return await getFutureChartPersistenceApi({ symbol, interval })
  } catch (error) {
    console.warn('Failed to load chart persistence', error)
    return null
  }
}

export const saveChartPersistence = async (payload: FutureChartPersistenceSaveParams) => {
  try {
    await saveFutureChartPersistenceApi(payload)
  } catch (error) {
    console.warn('Failed to save chart persistence', error)
  }
}

export const loadLocalStudyTemplate = () => {
  try {
    return parseChartJson<object>(window.localStorage.getItem(LOCAL_STUDY_TEMPLATE_KEY))
  } catch (error) {
    console.warn('Failed to load local study template', error)
    return null
  }
}

export const saveLocalStudyTemplate = (currentWidget: TradingViewWidget) => {
  const activeChart = currentWidget.activeChart()
  const createStudyTemplate = activeChart.createStudyTemplate
  if (!createStudyTemplate) {
    return
  }

  try {
    const content = stringifyChartJson(
      createStudyTemplate.call(activeChart, {
        saveSymbol: false,
        saveInterval: false,
      }),
    )
    if (content) {
      window.localStorage.setItem(LOCAL_STUDY_TEMPLATE_KEY, content)
    }
  } catch (error) {
    console.warn('Failed to save local study template', error)
  }
}

export const getDrawingsStateContent = (currentWidget: TradingViewWidget) => {
  const activeChart = currentWidget.activeChart()
  if (!activeChart.getLineToolsState) {
    return null
  }

  try {
    return stringifyChartJson(activeChart.getLineToolsState())
  } catch (error) {
    console.warn('Failed to collect chart drawings state', error)
    return null
  }
}

export const restoreChartPersistence = async (
  currentWidget: TradingViewWidget,
  persistence: FutureChartPersistence | null,
) => {
  let appliedLocalStudyTemplate = false

  try {
    const activeChart = currentWidget.activeChart()
    const localStudyTemplate = loadLocalStudyTemplate()
    const applyStudyTemplate = activeChart.applyStudyTemplate
    if (localStudyTemplate && applyStudyTemplate) {
      appliedLocalStudyTemplate = true
      applyStudyTemplate.call(activeChart, localStudyTemplate)
    }

    const applyLineToolsState = activeChart.applyLineToolsState
    const drawingsState = parseChartJson<TradingViewLineToolsAndGroupsState>(persistence?.drawings_content)
    if (drawingsState && applyLineToolsState) {
      await applyLineToolsState.call(activeChart, drawingsState)
    }
  } catch (error) {
    console.warn('Failed to restore chart persistence', error)
  }

  return {
    appliedLocalStudyTemplate,
  }
}
