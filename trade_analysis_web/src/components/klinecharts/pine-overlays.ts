import { registerOverlay, type OverlayCreate } from "klinecharts"

import type {
  PineBoxDrawing,
  PineLabelDrawing,
  PineLineDrawing,
} from "@/api/modules"

type PineOverlayCreate = OverlayCreate

let registered = false

const createLabelTriangle = (x: number, y: number, style?: string) => {
  if (style === "style_label_down") {
    return [
      { x, y },
      { x: x - 6, y: y - 9 },
      { x: x + 6, y: y - 9 },
    ]
  }

  return [
    { x, y },
    { x: x - 6, y: y + 9 },
    { x: x + 6, y: y + 9 },
  ]
}

const lineStyle = (style?: string) => (style === "dashed" || style === "dotted" ? "dashed" : "solid")

export const registerPineDrawingOverlays = () => {
  if (registered) {
    return
  }

  registerOverlay<PineLabelDrawing>({
    name: "pine_label",
    totalStep: 1,
    lock: true,
    needDefaultPointFigure: false,
    createPointFigures: ({ coordinates, overlay }) => {
      const coordinate = coordinates[0]
      if (!coordinate) {
        return []
      }

      const drawing = overlay.extendData
      return [{
        type: "polygon",
        attrs: {
          coordinates: createLabelTriangle(coordinate.x, coordinate.y, drawing.style),
        },
        styles: {
          style: "fill",
          color: drawing.color ?? "#2962ff",
        },
        ignoreEvent: true,
      }]
    },
  })

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
        styles: {
          style: lineStyle(drawing.style),
          size: drawing.width ?? 1,
          color: drawing.color ?? "#2962ff",
        },
        ignoreEvent: true,
      }]
    },
  })

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

  registered = true
}

const toOverlayPoint = (point: { timestamp?: number; price?: number }) => {
  if (!Number.isFinite(point.timestamp) || !Number.isFinite(point.price)) {
    return undefined
  }

  return { timestamp: point.timestamp as number, value: point.price as number }
}

export const createPineDrawingOverlays = (
  groupId: string,
  drawings: {
    labels: PineLabelDrawing[]
    lines: PineLineDrawing[]
    boxes: PineBoxDrawing[]
  },
): PineOverlayCreate[] => {
  const overlays: PineOverlayCreate[] = []

  for (const drawing of drawings.labels) {
    const point = toOverlayPoint(drawing)
    if (point) {
      overlays.push({ name: "pine_label", groupId, points: [point], extendData: drawing, lock: true })
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
