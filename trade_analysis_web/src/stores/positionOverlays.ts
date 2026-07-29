import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

export type PositionDirection = 'long' | 'short'

export interface PositionOverlay {
  id: string
  symbol: string
  direction: PositionDirection
  openPrice: number
  quantity: number
  openTime: string
  note: string
  closedAt?: string
}

const STORAGE_KEY = 'trade-analysis:position-overlays'

const loadPositions = (): PositionOverlay[] => {
  try {
    const rawValue = window.localStorage.getItem(STORAGE_KEY)
    const positions = rawValue ? JSON.parse(rawValue) : []
    return Array.isArray(positions) ? positions : []
  } catch {
    return []
  }
}

export const usePositionOverlayStore = defineStore('position-overlays', () => {
  const positions = ref<PositionOverlay[]>(loadPositions())

  watch(positions, (items) => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  }, { deep: true })

  const addPosition = (position: Omit<PositionOverlay, 'id'>) => {
    positions.value = [...positions.value, {
      ...position,
      id: globalThis.crypto.randomUUID(),
    }]
  }

  const updatePosition = (positionId: string, position: Omit<PositionOverlay, 'id' | 'closedAt'>) => {
    positions.value = positions.value.map((item) => (
      item.id === positionId ? { ...item, ...position } : item
    ))
  }

  const closePosition = (positionId: string) => {
    positions.value = positions.value.map((position) => (
      position.id === positionId ? { ...position, closedAt: new Date().toISOString() } : position
    ))
  }

  const deletePosition = (positionId: string) => {
    positions.value = positions.value.filter((position) => position.id !== positionId)
  }

  return { positions, addPosition, updatePosition, closePosition, deletePosition }
})
