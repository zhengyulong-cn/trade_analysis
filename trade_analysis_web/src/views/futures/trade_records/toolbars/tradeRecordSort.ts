import { TRADE_RECORD_VIEW_STORAGE_KEY } from "./public"
import type { TradeRecord, TradeRecordColumn } from "@/api/modules"

export type SortDirection = "asc" | "desc"

export interface SortCondition {
  id: string
  column_key: string
  direction: SortDirection
}

export interface TradeRecordViewState {
  sort_enabled: boolean
  sort_conditions: SortCondition[]
}

let sortConditionSeed = 1

export const getSortableColumns = (columns: TradeRecordColumn[]) =>
  columns.filter((item) => ["string", "number", "datetime"].includes(item.data_type))

export const compareTradeRecordValues = (
  column: TradeRecordColumn,
  firstValue: unknown,
  secondValue: unknown,
) => {
  const isFirstEmpty = firstValue === null || firstValue === undefined || firstValue === ""
  const isSecondEmpty = secondValue === null || secondValue === undefined || secondValue === ""

  if (isFirstEmpty && isSecondEmpty) {
    return 0
  }
  if (isFirstEmpty) {
    return 1
  }
  if (isSecondEmpty) {
    return -1
  }

  if (column.data_type === "number") {
    const firstNumber = Number(firstValue)
    const secondNumber = Number(secondValue)
    if (!Number.isFinite(firstNumber) || !Number.isFinite(secondNumber)) {
      return String(firstValue).localeCompare(String(secondValue), "zh-CN", { numeric: true })
    }
    return firstNumber - secondNumber
  }

  if (column.data_type === "datetime") {
    const firstTime = new Date(String(firstValue)).getTime()
    const secondTime = new Date(String(secondValue)).getTime()
    if (!Number.isFinite(firstTime) || !Number.isFinite(secondTime)) {
      return String(firstValue).localeCompare(String(secondValue), "zh-CN", { numeric: true })
    }
    return firstTime - secondTime
  }

  return String(firstValue).localeCompare(String(secondValue), "zh-CN", {
    numeric: true,
    sensitivity: "base",
  })
}

export const createSortCondition = (sortableColumns: TradeRecordColumn[], columnKey?: string): SortCondition => ({
  id: `sort-condition-${sortConditionSeed++}`,
  column_key: columnKey ?? sortableColumns[0]?.column_key ?? "",
  direction: "asc",
})

export const normalizeSortConditions = (
  items: SortCondition[],
  sortableColumns: TradeRecordColumn[],
): SortCondition[] => {
  const validColumnKeys = new Set(sortableColumns.map((column) => column.column_key))
  return items
    .filter((item) => validColumnKeys.has(item.column_key))
    .map((item) => ({
      id: item.id || `sort-condition-${sortConditionSeed++}`,
      column_key: item.column_key,
      direction: item.direction === "desc" ? "desc" : "asc",
    }))
}

export const sortTradeRecords = (
  records: TradeRecord[],
  sortableColumns: TradeRecordColumn[],
  sortEnabled: boolean,
  sortConditions: SortCondition[],
) => {
  if (!sortEnabled || !sortConditions.length) {
    return records
  }

  const conditionColumns = new Map(sortableColumns.map((column) => [column.column_key, column]))

  return [...records].sort((first, second) => {
    for (const condition of sortConditions) {
      const column = conditionColumns.get(condition.column_key)
      if (!column) {
        continue
      }

      const firstValue = first.data_json[column.column_key]
      const secondValue = second.data_json[column.column_key]
      const comparison = compareTradeRecordValues(column, firstValue, secondValue)
      if (comparison !== 0) {
        return condition.direction === "asc" ? comparison : -comparison
      }
    }

    return first.trade_record_id - second.trade_record_id
  })
}

export const readTradeRecordViewState = (): TradeRecordViewState | null => {
  try {
    const raw = window.localStorage.getItem(TRADE_RECORD_VIEW_STORAGE_KEY)
    if (!raw) {
      return null
    }

    const parsed = JSON.parse(raw) as Partial<TradeRecordViewState>
    return {
      sort_enabled: Boolean(parsed.sort_enabled),
      sort_conditions: Array.isArray(parsed.sort_conditions)
        ? (parsed.sort_conditions as SortCondition[])
        : [],
    }
  } catch {
    return null
  }
}

export const saveTradeRecordViewState = (payload: TradeRecordViewState) => {
  window.localStorage.setItem(TRADE_RECORD_VIEW_STORAGE_KEY, JSON.stringify(payload))
}
