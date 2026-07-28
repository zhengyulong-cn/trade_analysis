import { registerOverlay, type OverlayCreate } from 'klinecharts'

interface PositionTextOverlayData {
  text: string
}

let registered = false

export const registerPositionTextOverlay = () => {
  if (registered) {
    return
  }

  registerOverlay<PositionTextOverlayData>({
    name: 'position_text',
    totalStep: 1,
    lock: true,
    needDefaultPointFigure: false,
    createPointFigures: ({ coordinates, overlay }) => {
      const coordinate = coordinates[0]
      if (!coordinate) {
        return []
      }
      const data = overlay.extendData
      return [{
        type: 'text',
        attrs: {
          x: coordinate.x + 6,
          y: coordinate.y - 6,
          text: data.text,
          align: 'left',
          baseline: 'bottom',
        },
        styles: { color: '#111827', size: 12, weight: '400' },
        ignoreEvent: true,
      }]
    },
  })
  registered = true
}

export const createPositionTextOverlay = (
  groupId: string,
  text: string,
  point: { timestamp: number; value: number },
): OverlayCreate => ({
  name: 'position_text',
  groupId,
  points: [point],
  extendData: { text },
  lock: true,
})
