import { registerOverlay, type OverlayCreate } from "klinecharts"

import type { PineLabelDrawing } from "@/api/modules"

export type PineChartLabelShape = "triangle_up" | "triangle_down"

export interface PineChartLabel {
  shape: PineChartLabelShape
  text: string
  tooltip: string
  color: string
  textColor: string
}

export interface PineLabelOverlayHandlers {
  onEnter?: (label: PineChartLabel, x?: number, y?: number) => void
  onMove?: (label: PineChartLabel, x?: number, y?: number) => void
  onLeave?: () => void
}

interface LabelMarkerGeometry {
  coordinates: Array<{ x: number; y: number }>
  textY: number
}

let registered = false

const createLabelMarker = (x: number, y: number, shape: PineChartLabelShape): LabelMarkerGeometry => {
  if (shape === "triangle_down") {
    return {
      coordinates: [{ x, y }, { x: x - 9, y: y - 14 }, { x: x + 9, y: y - 14 }],
      textY: y - 7,
    }
  }

  return {
    coordinates: [{ x, y }, { x: x - 9, y: y + 14 }, { x: x + 9, y: y + 14 }],
    textY: y + 7,
  }
}

const toPineChartLabel = (drawing: PineLabelDrawing): PineChartLabel => {
  const tooltip = drawing.text?.trim() ?? ""
  return {
    shape: drawing.style === "style_label_down" ? "triangle_down" : "triangle_up",
    text: tooltip.length <= 3 ? tooltip : "...",
    tooltip,
    color: drawing.color ?? "#2962ff",
    textColor: drawing.textColor ?? "#ffffff",
  }
}

export const registerPineLabelOverlay = () => {
  if (registered) {
    return
  }

  registerOverlay<PineChartLabel>({
    name: "pine_label",
    totalStep: 1,
    lock: true,
    needDefaultPointFigure: false,
    createPointFigures: ({ coordinates, overlay }) => {
      const coordinate = coordinates[0]
      if (!coordinate) {
        return []
      }

      const label = overlay.extendData
      const marker = createLabelMarker(coordinate.x, coordinate.y, label.shape)
      return [
        {
          type: "polygon",
          attrs: { coordinates: marker.coordinates },
          styles: { style: "fill", color: label.color },
        },
        {
          type: "text",
          attrs: {
            x: coordinate.x,
            y: marker.textY,
            text: label.text,
            align: "center",
            baseline: "middle",
          },
          styles: { color: label.textColor, size: 9, weight: "600" },
          ignoreEvent: true,
        },
      ]
    },
  })
  registered = true
}

export const createPineLabelOverlay = (
  groupId: string,
  drawing: PineLabelDrawing,
  point: { timestamp: number; value: number },
  handlers: PineLabelOverlayHandlers,
): OverlayCreate => {
  const label = toPineChartLabel(drawing)
  return {
    name: "pine_label",
    groupId,
    points: [point],
    extendData: label,
    lock: true,
    onMouseEnter: ({ x, y }) => handlers.onEnter?.(label, x, y),
    onMouseMove: ({ x, y }) => handlers.onMove?.(label, x, y),
    onMouseLeave: () => handlers.onLeave?.(),
  }
}
