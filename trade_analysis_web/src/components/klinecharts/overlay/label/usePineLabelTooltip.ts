import { onBeforeUnmount, ref, type Ref } from "vue"

import type { PineChartLabel } from "./pine-label-overlay"

interface PineLabelTooltipState {
  visible: boolean
  text: string
  x: number
  y: number
}

export const usePineLabelTooltip = (containerRef: Ref<HTMLElement | undefined>) => {
  const tooltip = ref<PineLabelTooltipState>({ visible: false, text: "", x: 0, y: 0 })
  let hideTimer: ReturnType<typeof setTimeout> | null = null

  const clearHideTimer = () => {
    if (hideTimer !== null) {
      clearTimeout(hideTimer)
      hideTimer = null
    }
  }

  const hide = () => {
    clearHideTimer()
    tooltip.value.visible = false
  }

  const show = (label: PineChartLabel, x?: number, y?: number) => {
    clearHideTimer()
    if (x === undefined || y === undefined || !label.tooltip) {
      return
    }

    const bounding = containerRef.value?.getBoundingClientRect()
    const maxX = Math.max(8, (bounding?.width ?? 0) - 250)
    const maxY = Math.max(8, (bounding?.height ?? 0) - 80)
    tooltip.value = {
      visible: true,
      text: label.tooltip,
      x: Math.min(Math.max(8, x + 12), maxX),
      y: Math.min(Math.max(8, y + 12), maxY),
    }
  }

  const scheduleHide = () => {
    clearHideTimer()
    if (tooltip.value.visible) {
      hideTimer = setTimeout(hide, 0)
    }
  }

  onBeforeUnmount(clearHideTimer)

  return { tooltip, clearHideTimer, hide, show, scheduleHide }
}
