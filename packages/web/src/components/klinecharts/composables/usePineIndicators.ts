import { ElMessage } from "element-plus"
import type { Chart } from 'klinecharts'
import { ref, type Ref } from 'vue'
import { usePineScriptsStore } from "@/stores/pineScripts"
import type { PineLabelOverlayHandlers } from '../overlay/label/pine-label-overlay'
import { createPineDrawingOverlays } from "../overlay/pine-drawing-overlays"
import { executePineScriptInBrowser, type LocalPineIndicatorResult } from "../indicator/pine-browser-executor"
import { createPineIndicator, removePineIndicator } from "../indicator/pine-indicator"

export const usePineIndicators = (
  getChart: () => Chart | null,
  selectedSymbol: Ref<string>,
  selectedPeriod: Ref<number>,
  labelHandlers: PineLabelOverlayHandlers,
) => {
  const selectedPineIndicatorIds = ref<number[]>([])
  const pineIndicatorLoadingIds = ref<number[]>([])
  const renderedPineIndicatorIds = new Set<number>()
  const pineScriptsStore = usePineScriptsStore()
  let latestRequestId = 0

  const groupId = (scriptId: number) => `pine-indicator-${scriptId}`

  const remove = (scriptId: number) => {
    const chart = getChart()
    chart?.removeOverlay({ groupId: groupId(scriptId) })
    removePineIndicator(chart, scriptId)
    renderedPineIndicatorIds.delete(scriptId)
  }

  const setLoading = (scriptId: number, loading: boolean) => {
    const ids = new Set(pineIndicatorLoadingIds.value)
    if (loading) {
      ids.add(scriptId)
    } else {
      ids.delete(scriptId)
    }
    pineIndicatorLoadingIds.value = [...ids]
  }

  const clear = () => {
    labelHandlers.onLeave?.()
    for (const scriptId of new Set([...renderedPineIndicatorIds, ...selectedPineIndicatorIds.value])) {
      remove(scriptId)
    }
  }

  const render = (result: LocalPineIndicatorResult) => {
    const chart = getChart()
    if (!chart) {
      return
    }
    remove(result.scriptId)
    const renderedAsIndicator = createPineIndicator(chart, result)
    const overlays = createPineDrawingOverlays(groupId(result.scriptId), result.drawings, labelHandlers)
    if (overlays.length) {
      chart.createOverlay(overlays)
    }
    if (renderedAsIndicator || overlays.length) {
      renderedPineIndicatorIds.add(result.scriptId)
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
      await pineScriptsStore.loadScripts()
      const script = pineScriptsStore.scriptsById.get(scriptId)
      if (!script || script.script_type !== "indicator") {
        throw new Error(`Pine indicator #${scriptId} was not found.`)
      }

      const result = await executePineScriptInBrowser(script, chart.getDataList())
      const isStillCurrent = getChart()
        && selectedSymbol.value === symbol
        && selectedPeriod.value === interval
        && selectedPineIndicatorIds.value.includes(scriptId)
      if (isStillCurrent) {
        render(result)
      }
    } catch (error) {
      if (selectedSymbol.value === symbol && selectedPeriod.value === interval) {
        const message = error instanceof Error ? error.message : "Unknown PineTS execution error."
        ElMessage.error(`Pine indicator #${scriptId}: ${message}`)
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
