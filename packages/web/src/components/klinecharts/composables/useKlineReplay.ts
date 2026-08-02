import { computed, ref } from "vue"
import type { Chart, Crosshair, KLineData } from "klinecharts"

export type ReplayMode = "live" | "selecting" | "paused" | "playing"

export const REPLAY_SPEED_OPTIONS = [
  { label: "1x", value: 800 },
  { label: "2x", value: 400 },
  { label: "5x", value: 160 },
]

interface UseKlineReplayOptions {
  getChart: () => Chart | null
  onEnterSelection: () => void
  onNextBar: (bar: KLineData) => void
  onExit: () => void
}

export const useKlineReplay = ({ getChart, onEnterSelection, onNextBar, onExit }: UseKlineReplayOptions) => {
  const mode = ref<ReplayMode>("live")
  const historicalBars = ref<KLineData[]>([])
  const replayBars = ref<KLineData[]>([])
  const cursor = ref(-1)
  const startIndex = ref(-1)
  const speed = ref(800)
  const selecting = ref(false)
  const selectionX = ref<number>()
  const isActive = computed(() => mode.value !== "live")
  const startTime = computed(() => {
    const bar = historicalBars.value[startIndex.value]
    return bar ? new Date(bar.timestamp).toLocaleString("zh-CN", { hour12: false }) : ""
  })
  let timer: number | undefined

  const clearTimer = () => {
    if (timer !== undefined) {
      window.clearInterval(timer)
      timer = undefined
    }
  }

  const setHistoricalBars = (bars: KLineData[]) => {
    historicalBars.value = bars
  }

  const getLocalBars = () => {
    if (mode.value === "live" || !historicalBars.value.length) {
      return undefined
    }
    return mode.value === "selecting"
      ? historicalBars.value
      : replayBars.value.slice(0, cursor.value + 1)
  }

  const clampStartIndex = (index: number) => {
    const lastIndex = historicalBars.value.length - 1
    return Math.max(0, Math.min(index, Math.max(0, lastIndex - 1)))
  }

  const reset = () => {
    clearTimer()
    mode.value = "live"
    replayBars.value = []
    cursor.value = -1
    startIndex.value = -1
    selecting.value = false
    selectionX.value = undefined
    getChart()?.setScrollEnabled(true)
  }

  const beginSelection = () => {
    if (historicalBars.value.length < 2) {
      return false
    }

    const resumeFromReplay = mode.value === "paused" || mode.value === "playing"
    const visibleRange = getChart()?.getVisibleRange()
    clearTimer()
    onEnterSelection()
    mode.value = "selecting"
    selectionX.value = undefined
    startIndex.value = clampStartIndex(
      resumeFromReplay
        ? cursor.value
        : Math.floor(((visibleRange?.from ?? 0) + (visibleRange?.to ?? historicalBars.value.length - 1)) / 2),
    )
    const chart = getChart()
    chart?.setScrollEnabled(false)
    if (resumeFromReplay) {
      chart?.resetData()
      chart?.scrollToDataIndex(startIndex.value)
    }
    return true
  }

  const start = () => {
    if (mode.value !== "selecting" || startIndex.value < 0) {
      return
    }

    replayBars.value = [...historicalBars.value]
    cursor.value = startIndex.value
    mode.value = "paused"
    const chart = getChart()
    chart?.resetData()
    chart?.scrollToRealTime()
  }

  const step = () => {
    if (mode.value !== "paused" && mode.value !== "playing") {
      return
    }
    const nextBar = replayBars.value[cursor.value + 1]
    if (!nextBar) {
      clearTimer()
      mode.value = "paused"
      return
    }

    cursor.value += 1
    onNextBar(nextBar)
  }

  const play = () => {
    if (mode.value === "playing") {
      return
    }
    mode.value = "playing"
    clearTimer()
    timer = window.setInterval(step, speed.value)
  }

  const pause = () => {
    clearTimer()
    if (mode.value === "playing") {
      mode.value = "paused"
    }
  }

  const setSpeed = (value: number) => {
    speed.value = value
    if (mode.value === "playing") {
      clearTimer()
      timer = window.setInterval(step, speed.value)
    }
  }

  const exit = () => {
    reset()
    onExit()
  }

  const onCrosshairChange = (data?: unknown) => {
    if (mode.value !== "selecting") {
      return
    }
    const x = (data as Crosshair | undefined)?.x
    if (!Number.isFinite(x)) {
      return
    }
    const point = getChart()?.convertFromPixel([{ x: x as number }])
    const index = Array.isArray(point) ? point[0]?.dataIndex : point?.dataIndex
    if (Number.isInteger(index)) {
      startIndex.value = clampStartIndex(index as number)
    }
    selectionX.value = x as number
  }

  const startSelectionDrag = () => {
    if (mode.value === "selecting") {
      selecting.value = true
    }
  }

  const stopSelectionDrag = () => {
    if (mode.value === "selecting" && selecting.value && startIndex.value >= 0) {
      start()
    }
    selecting.value = false
  }

  const dispose = () => {
    clearTimer()
  }

  return {
    mode,
    historicalBars,
    speed,
    startTime,
    selectionX,
    isActive,
    setHistoricalBars,
    getLocalBars,
    reset,
    beginSelection,
    play,
    pause,
    step,
    setSpeed,
    exit,
    onCrosshairChange,
    startSelectionDrag,
    stopSelectionDrag,
    dispose,
  }
}
