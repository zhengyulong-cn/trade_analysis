import type { Chart } from 'klinecharts'
import type { Ref } from 'vue'
import type { PositionOverlay } from '@/stores/positionOverlays'
import { createPositionTextOverlay } from '../overlay/position-text-overlay'

const GROUP_ID = 'position-overlays'

export const usePositionChartOverlays = (
  getChart: () => Chart | null,
  selectedSymbol: Ref<string>,
  positions: Ref<PositionOverlay[]>,
) => {
  const clear = () => {
    getChart()?.removeOverlay({ groupId: GROUP_ID })
  }

  const render = () => {
    const chart = getChart()
    if (!chart || !selectedSymbol.value) {
      return
    }
    clear()
    const latestBar = chart.getDataList().at(-1)
    if (!latestBar) {
      return
    }
    const overlays = positions.value
      .filter((position) => position.symbol === selectedSymbol.value)
      .flatMap((position) => {
        const openTimestamp = new Date(position.openTime).getTime()
        if (!Number.isFinite(openTimestamp)) {
          return []
        }
        const price = position.openPrice
        const color = position.direction === 'long' ? '#dc2626' : '#2563eb'
        const endTimestamp = Math.max(openTimestamp, latestBar.timestamp)
        const directionLabel = position.direction === 'long' ? '多' : '空'
        const label = `${directionLabel} | 开仓价 ${price.toFixed(1)} | 手数 ${position.quantity}`
        return [
          {
            name: 'pine_line',
            groupId: GROUP_ID,
            points: [
              { timestamp: openTimestamp, value: price },
              { timestamp: endTimestamp, value: price },
            ],
            extendData: { id: position.id, style: 'dashed', color, width: 1 },
            lock: true,
          },
          createPositionTextOverlay(GROUP_ID, label, { timestamp: openTimestamp, value: price }),
        ]
      })
    if (overlays.length) {
      chart.createOverlay(overlays)
    }
  }

  return { clear, render }
}
