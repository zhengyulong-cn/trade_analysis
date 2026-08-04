import { registerOverlay, type OverlayCreate } from "klinecharts"

import type { PineLabelDrawing } from "@/api/modules"

export type PineChartLabelShape = "triangle_up" | "triangle_down"

export interface PineChartLabel {
  shape: PineChartLabelShape
  text: string
  color: string
  textColor: string
}

interface LabelMarkerGeometry {
  pointerCoordinates: Array<{ x: number; y: number }>
  labelX: number
  labelY: number
  labelWidth: number
  labelHeight: number
  textY: number
}

let registered = false

const getLabelWidth = (text: string) => {
  const contentWidth = Array.from(text).reduce((width, character) => (
    width + (character.charCodeAt(0) > 0xff ? 9 : 5.5)
  ), 0)
  return Math.max(24, contentWidth + 12)
}

const createLabelMarker = (
  x: number,
  y: number,
  shape: PineChartLabelShape,
  text: string,
): LabelMarkerGeometry => {
  const labelWidth = getLabelWidth(text)
  const labelHeight = 18
  const pointerHeight = 6
  if (shape === "triangle_down") {
    return {
      pointerCoordinates: [{ x, y }, { x: x - 6, y: y - pointerHeight }, { x: x + 6, y: y - pointerHeight }],
      labelX: x - labelWidth / 2,
      labelY: y - pointerHeight - labelHeight,
      labelWidth,
      labelHeight,
      textY: y - pointerHeight - labelHeight / 2,
    }
  }

  return {
    pointerCoordinates: [{ x, y }, { x: x - 6, y: y + pointerHeight }, { x: x + 6, y: y + pointerHeight }],
    labelX: x - labelWidth / 2,
    labelY: y + pointerHeight,
    labelWidth,
    labelHeight,
    textY: y + pointerHeight + labelHeight / 2,
  }
}

const toPineChartLabel = (drawing: PineLabelDrawing): PineChartLabel => {
  return {
    shape: drawing.style === "style_label_up" ? "triangle_up" : "triangle_down",
    text: drawing.text?.trim() ?? "",
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
      const marker = createLabelMarker(coordinate.x, coordinate.y, label.shape, label.text)
      return [
        {
          type: "polygon",
          attrs: { coordinates: marker.pointerCoordinates },
          styles: { style: "fill", color: label.color },
        },
        {
          type: "rect",
          attrs: {
            x: marker.labelX,
            y: marker.labelY,
            width: marker.labelWidth,
            height: marker.labelHeight,
          },
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
          styles: { color: label.textColor, size: 9, weight: "600", backgroundColor: "" },
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
): OverlayCreate => {
  const label = toPineChartLabel(drawing)
  return {
    name: "pine_label",
    groupId,
    points: [point],
    extendData: label,
    lock: true,
  }
}
