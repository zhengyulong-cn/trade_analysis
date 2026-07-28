import { registerOverlay, type OverlayCreate } from "klinecharts"

import type { PineBoxDrawing, PineIndicatorDrawings, PineLineDrawing } from "@/api/modules"
import {
  createPineLabelOverlay,
  registerPineLabelOverlay,
  type PineLabelOverlayHandlers,
} from "./label/pine-label-overlay"

let registered = false

const lineStyle = (style?: string) => (style === "dashed" || style === "dotted" ? "dashed" : "solid")

const toOverlayPoint = (point: { timestamp?: number; price?: number }) => {
  if (!Number.isFinite(point.timestamp) || !Number.isFinite(point.price)) {
    return undefined
  }
  return { timestamp: point.timestamp as number, value: point.price as number }
}

const registerPineLineOverlay = () => {
  registerOverlay<PineLineDrawing>({
    name: "pine_line",
    totalStep: 2,
    lock: true,
    needDefaultPointFigure: false,
    createPointFigures: ({ coordinates, overlay }) => {
      const start = coordinates[0]
      const end = coordinates[1]
      if (!start || !end) {
        return []
      }
      const drawing = overlay.extendData
      return [{
        type: "line",
        attrs: { coordinates: [start, end] },
        styles: { style: lineStyle(drawing.style), size: drawing.width ?? 1, color: drawing.color ?? "#2962ff" },
        ignoreEvent: true,
      }]
    },
  })
}

const registerPineBoxOverlay = () => {
  registerOverlay<PineBoxDrawing>({
    name: "pine_box",
    totalStep: 2,
    lock: true,
    needDefaultPointFigure: false,
    createPointFigures: ({ coordinates, overlay }) => {
      const start = coordinates[0]
      const end = coordinates[1]
      if (!start || !end) {
        return []
      }
      const drawing = overlay.extendData
      return [{
        type: "rect",
        attrs: {
          x: Math.min(start.x, end.x),
          y: Math.min(start.y, end.y),
          width: Math.abs(end.x - start.x),
          height: Math.abs(end.y - start.y),
        },
        styles: {
          style: drawing.backgroundColor ? "stroke_fill" : "stroke",
          color: drawing.backgroundColor ?? "transparent",
          borderColor: drawing.borderColor ?? "#2962ff",
          borderSize: drawing.borderWidth ?? 1,
          borderStyle: lineStyle(drawing.borderStyle),
        },
        ignoreEvent: true,
      }]
    },
  })
}

export const registerPineDrawingOverlays = () => {
  if (registered) {
    return
  }
  registerPineLabelOverlay()
  registerPineLineOverlay()
  registerPineBoxOverlay()
  registered = true
}

export const createPineDrawingOverlays = (
  groupId: string,
  drawings: PineIndicatorDrawings,
  labelHandlers: PineLabelOverlayHandlers = {},
): OverlayCreate[] => {
  const overlays: OverlayCreate[] = []
  for (const drawing of drawings.labels) {
    const point = toOverlayPoint(drawing)
    if (point) {
      overlays.push(createPineLabelOverlay(groupId, drawing, point, labelHandlers))
    }
  }
  for (const drawing of drawings.lines) {
    const start = toOverlayPoint(drawing.start)
    const end = toOverlayPoint(drawing.end)
    if (start && end) {
      overlays.push({ name: "pine_line", groupId, points: [start, end], extendData: drawing, lock: true })
    }
  }
  for (const drawing of drawings.boxes) {
    const start = toOverlayPoint({ ...drawing.start, price: drawing.top })
    const end = toOverlayPoint({ ...drawing.end, price: drawing.bottom })
    if (start && end) {
      overlays.push({ name: "pine_box", groupId, points: [start, end], extendData: drawing, lock: true })
    }
  }
  return overlays
}
