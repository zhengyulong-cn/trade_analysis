import { ElMessage } from 'element-plus'
import type { Chart } from 'klinecharts'
import { ref, type Ref } from 'vue'
import { executePineIndicatorApi, type PineIndicatorExecuteResult } from '@/api/modules'
import { createPineDrawingOverlays, createPinePlotOverlays } from '../overlay/pine-drawing-overlays'
import type { PineLabelOverlayHandlers } from '../overlay/label/pine-label-overlay'

export const usePineIndicators = (
  getChart: () => Chart | null,
  selectedSymbol: Ref<string>,
  selectedPeriod: Ref<number>,
  labelHandlers: PineLabelOverlayHandlers,
) => {
  const selectedPineIndicatorIds = ref<number[]>([])
  const pineIndicatorLoadingIds = ref<number[]>([])
  const renderedPineIndicatorIds = new Set<number>()
  let latestRequestId = 0

  const groupId = (scriptId: number) => `pine-indicator-${scriptId}`

  const setLoading = (scriptId: number, loading: boolean) => {
    const ids = new Set(pineIndicatorLoadingIds.value)
    if (loading) {
      ids.add(scriptId)
    } else {
      ids.delete(scriptId)
    }
    pineIndicatorLoadingIds.value = [...ids]
  }

  const remove = (scriptId: number) => {
    getChart()?.removeOverlay({ groupId: groupId(scriptId) })
    renderedPineIndicatorIds.delete(scriptId)
  }

  const clear = () => {
    labelHandlers.onLeave?.()
    for (const scriptId of new Set([...renderedPineIndicatorIds, ...selectedPineIndicatorIds.value])) {
      remove(scriptId)
    }
  }

  const render = (result: PineIndicatorExecuteResult) => {
    const chart = getChart()
    if (!chart) {
      return
    }
    remove(result.script_id)
    const indicatorGroupId = groupId(result.script_id)
    const overlays = [
      ...createPinePlotOverlays(indicatorGroupId, result.plots),
      ...createPineDrawingOverlays(indicatorGroupId, result.drawings, labelHandlers),
    ]
    if (overlays.length) {
      chart.createOverlay(overlays)
      renderedPineIndicatorIds.add(result.script_id)
    }
  }

  const load = async (scriptId: number) => {
    const chart = getChart()
    const symbol = selectedSymbol.value
    const interval = selectedPeriod.value
    if (!chart || !symbol || !selectedPineIndicatorIds.value.includes(scriptId)) {
      return
    }

    const requestId = ++latestRequestId
    setLoading(scriptId, true)
    try {
      const result = await executePineIndicatorApi({ script_id: scriptId, symbol, interval, limit: 1000 })
      const isStillCurrent = getChart()
        && selectedSymbol.value === symbol
        && selectedPeriod.value === interval
        && selectedPineIndicatorIds.value.includes(scriptId)
      if (isStillCurrent) {
        render(result)
      }
    } catch {
      if (selectedSymbol.value === symbol && selectedPeriod.value === interval) {
        ElMessage.error(`Failed to load Pine indicator #${scriptId}.`)
      }
    } finally {
      if (requestId <= latestRequestId) {
        setLoading(scriptId, false)
      }
    }
  }

  const reload = () => {
    for (const scriptId of selectedPineIndicatorIds.value) {
      void load(scriptId)
    }
  }

  const update = (scriptIds: number[]) => {
    const nextIds = [...new Set(scriptIds)]
    const nextIdSet = new Set(nextIds)
    for (const scriptId of selectedPineIndicatorIds.value) {
      if (!nextIdSet.has(scriptId)) {
        remove(scriptId)
      }
    }

    const currentIdSet = new Set(selectedPineIndicatorIds.value)
    selectedPineIndicatorIds.value = nextIds
    for (const scriptId of nextIds) {
      if (!currentIdSet.has(scriptId)) {
        void load(scriptId)
      }
    }
  }

  return { selectedPineIndicatorIds, pineIndicatorLoadingIds, clear, load, reload, update }
}
