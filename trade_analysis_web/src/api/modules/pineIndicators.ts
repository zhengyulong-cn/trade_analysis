import axios from "@/api/axios"

export interface PineIndicatorExecuteParams {
  script_id: number
  symbol: string
  interval: number
  limit?: number
}

export interface PineIndicatorExecuteResult {
  script_id: number
  script_name: string
  symbol: string
  interval: number
  bar_count: number
  indicator: Record<string, unknown>
  plots: PineIndicatorPlot[]
  drawings: PineIndicatorDrawings
  warnings: Array<Record<string, unknown>>
}

export interface PineIndicatorPlot {
  key: string
  title?: string
  options?: Record<string, unknown>
  data: Array<Record<string, unknown>>
}

export interface PineDrawingPoint {
  timestamp?: number
  barIndex?: number
  price?: number
}

export interface PineLabelDrawing extends PineDrawingPoint {
  id: string
  title?: string
  text?: string
  style?: string
  color?: string
  textColor?: string
}

export interface PineLineDrawing {
  id: string
  title?: string
  start: PineDrawingPoint
  end: PineDrawingPoint
  extend?: string
  style?: string
  color?: string
  width?: number
}

export interface PineBoxDrawing {
  id: string
  title?: string
  start: PineDrawingPoint
  end: PineDrawingPoint
  top?: number
  bottom?: number
  extend?: string
  borderColor?: string
  borderStyle?: string
  borderWidth?: number
  backgroundColor?: string
  text?: string
}

export interface PineIndicatorDrawings {
  labels: PineLabelDrawing[]
  lines: PineLineDrawing[]
  boxes: PineBoxDrawing[]
}

export const executePineIndicatorApi = (params: PineIndicatorExecuteParams) => {
  return axios.post<PineIndicatorExecuteResult>("/pine-indicators/execute", params) as unknown as Promise<PineIndicatorExecuteResult>
}
