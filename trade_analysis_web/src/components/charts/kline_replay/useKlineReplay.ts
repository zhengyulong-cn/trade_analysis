import { ElMessage } from 'element-plus'
import { createApp, computed, h, ref, type Ref } from 'vue'
import { getTradingViewBars, normalizeTimeToMilliseconds } from '@/components/charts/chartDatafeed'
import type { KLineItem } from '@/components/charts/chartModels'
import type { TradingViewWidget } from '@/components/charts/tradingViewTypes'

interface UseKLineReplayOptions {
  hoveredKLine: Ref<KLineItem | null>
  emitCrosshairMove: (value: KLineItem | null) => void
  getSortedKLineList: () => KLineItem[]
  getCreateWidgetToken: () => number
  getWidget: () => TradingViewWidget | null
  pushReplayBar: (bar: ReturnType<typeof getTradingViewBars>[number]) => void
}

const formatReplayTime = (targetBar: KLineItem | null) => {
  if (!targetBar) {
    return ''
  }

  const targetDate = new Date(normalizeTimeToMilliseconds(targetBar.time))
  const year = targetDate.getFullYear()
  const month = String(targetDate.getMonth() + 1).padStart(2, '0')
  const day = String(targetDate.getDate()).padStart(2, '0')
  const hour = String(targetDate.getHours()).padStart(2, '0')
  const minute = String(targetDate.getMinutes()).padStart(2, '0')

  return `${year}-${month}-${day} ${hour}:${minute}`
}

export const useKLineReplay = ({
  hoveredKLine,
  emitCrosshairMove,
  getSortedKLineList,
  getCreateWidgetToken,
  getWidget,
  pushReplayBar,
}: UseKLineReplayOptions) => {
  const isReplayMode = ref(false)
  const replayCursorIndex = ref<number | null>(null)
  const isReplayPanelOpen = ref(false)
  const replaySelectedTime = ref<Date | null>(null)
  const replayToggleButton = ref<HTMLElement | string | null>(null)

  const replayCursorBar = computed(() => {
    if (!isReplayMode.value) {
      return null
    }

    const cursorIndex = replayCursorIndex.value
    if (cursorIndex === null || cursorIndex < 0) {
      return null
    }

    return getSortedKLineList()[cursorIndex] ?? null
  })

  const displayedKLineList = computed(() => {
    const sortedList = getSortedKLineList()
    if (!isReplayMode.value) {
      return sortedList
    }

    const cursorIndex = replayCursorIndex.value
    if (cursorIndex === null || cursorIndex < 0) {
      return sortedList
    }

    return sortedList.slice(0, cursorIndex + 1)
  })

  const hasReplayNext = computed(() => {
    const cursorIndex = replayCursorIndex.value
    if (!isReplayMode.value || cursorIndex === null) {
      return false
    }

    return cursorIndex < getSortedKLineList().length - 1
  })

  const replayTimeLabel = computed(() => {
    return formatReplayTime(replayCursorBar.value)
  })

  const replaySelectionRange = computed(() => {
    const sortedList = getSortedKLineList()
    const firstBar = sortedList[0]
    const lastBar = sortedList[sortedList.length - 1]
    return {
      start: firstBar ? normalizeTimeToMilliseconds(firstBar.time) : null,
      end: lastBar ? normalizeTimeToMilliseconds(lastBar.time) : null,
    }
  })

  const ensureReplaySelection = () => {
    if (replaySelectedTime.value) {
      return
    }

    const preferredBar = hoveredKLine.value ?? getSortedKLineList()[0] ?? null
    if (preferredBar) {
      replaySelectedTime.value = new Date(normalizeTimeToMilliseconds(preferredBar.time))
    }
  }

  const openReplayPanel = () => {
    isReplayPanelOpen.value = true
    if (!isReplayMode.value) {
      ensureReplaySelection()
    }
  }

  const toggleReplayPanel = () => {
    isReplayPanelOpen.value = !isReplayPanelOpen.value
    if (isReplayPanelOpen.value && !isReplayMode.value) {
      ensureReplaySelection()
    }
  }

  const teardownReplayHeaderButtons = (targetWidget?: TradingViewWidget | null) => {
    const currentWidget = targetWidget ?? getWidget()
    if (currentWidget?.removeButton && replayToggleButton.value) {
      currentWidget.removeButton(replayToggleButton.value)
    } else if (replayToggleButton.value instanceof HTMLElement) {
      replayToggleButton.value.remove()
    }

    replayToggleButton.value = null
  }

  const setupReplayHeaderButtons = async (currentWidget: TradingViewWidget, token: number) => {
    if (!currentWidget.headerReady || !currentWidget.createButton) {
      return
    }

    await currentWidget.headerReady()

    if (token !== getCreateWidgetToken() || getWidget() !== currentWidget) {
      return
    }

    teardownReplayHeaderButtons(currentWidget)

    replayToggleButton.value = currentWidget.createButton({
      align: 'left',
      useTradingViewStyle: true,
      text: isReplayMode.value ? '复盘' : '复盘中',
      title: '复盘功能',
      onClick: toggleReplayPanel,
    })
  }

  const enterReplayMode = () => {
    if (!replaySelectedTime.value) {
      ElMessage.warning('请先选复盘起始时间')
      return
    }

    const targetTime = replaySelectedTime.value.getTime()
    const sortedList = getSortedKLineList()
    const targetIndex = sortedList.findIndex(
      (item) => normalizeTimeToMilliseconds(item.time) >= targetTime,
    )

    if (targetIndex < 0) {
      ElMessage.warning('不能根据选定时间确定K线')
      return
    }

    hoveredKLine.value = sortedList[targetIndex] ?? null
    replayCursorIndex.value = targetIndex
    isReplayMode.value = true
    isReplayPanelOpen.value = true
  }

  const stepReplayForward = () => {
    if (!isReplayMode.value) {
      return
    }

    const cursorIndex = replayCursorIndex.value
    const sortedList = getSortedKLineList()
    if (cursorIndex === null || cursorIndex >= sortedList.length - 1) {
      return
    }

    const nextCursorIndex = cursorIndex + 1
    const nextBar = sortedList[nextCursorIndex]
    if (!nextBar) {
      return
    }

    replayCursorIndex.value = nextCursorIndex
    hoveredKLine.value = nextBar
    emitCrosshairMove(nextBar)

    const replayBar = getTradingViewBars([nextBar])[0]
    if (replayBar) {
      pushReplayBar(replayBar)
    }
  }

  const exitReplayMode = () => {
    isReplayMode.value = false
    replayCursorIndex.value = null
    ensureReplaySelection()
  }

  const resetReplayOnDataChange = () => {
    hoveredKLine.value = null
    emitCrosshairMove(null)
    if (isReplayMode.value || replayCursorIndex.value !== null) {
      exitReplayMode()
      return true
    }
    return false
  }

  return {
    displayedKLineList,
    hasReplayNext,
    isReplayMode,
    isReplayPanelOpen,
    openReplayPanel,
    replayCursorBar,
    replayCursorIndex,
    replaySelectedTime,
    replaySelectionRange,
    replayTimeLabel,
    setupReplayHeaderButtons,
    stepReplayForward,
    teardownReplayHeaderButtons,
    toggleReplayPanel,
    enterReplayMode,
    exitReplayMode,
    ensureReplaySelection,
    resetReplayOnDataChange,
  }
}

export type KLineReplayController = ReturnType<typeof useKLineReplay>
