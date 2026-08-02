import type { TradeRecord, TradeRecordColumn } from "@/api/modules"
import type { SortCondition } from "./tradeRecordSort"

export type FilterLogic = "all" | "any"

export type FilterOperator =
  | "true"
  | "false"
  | "eq"
  | "ne"
  | "contains"
  | "not_contains"
  | "gt"
  | "gte"
  | "lt"
  | "lte"
  | "before"
  | "after"
  | "empty"
  | "not_empty"

export interface FilterCondition {
  id: string
  column_key: string
  operator: FilterOperator
  value: unknown
}

export interface TradeRecordManagerViewState {
  sort_enabled: boolean
  sort_conditions: SortCondition[]
  filter_enabled: boolean
  filter_logic: FilterLogic
  filter_conditions: FilterCondition[]
}

export interface FilterOperatorOption {
  label: string
  value: FilterOperator
}

const STORAGE_KEY = "trade-record-manager-view-state-v2"

const OPERATOR_OPTIONS: Record<TradeRecordColumn["data_type"], FilterOperatorOption[]> = {
  bool: [
    { label: "True", value: "true" },
    { label: "False", value: "false" },
    { label: "为空", value: "empty" },
    { label: "不为空", value: "not_empty" },
  ],
  string: [
    { label: "等于", value: "eq" },
    { label: "不等于", value: "ne" },
    { label: "包含", value: "contains" },
    { label: "不包含", value: "not_contains" },
    { label: "为空", value: "empty" },
    { label: "不为空", value: "not_empty" },
  ],
  number: [
    { label: "大于", value: "gt" },
    { label: "大于等于", value: "gte" },
    { label: "等于", value: "eq" },
    { label: "不等于", value: "ne" },
    { label: "小于", value: "lt" },
    { label: "小于等于", value: "lte" },
    { label: "为空", value: "empty" },
    { label: "不为空", value: "not_empty" },
  ],
  datetime: [
    { label: "等于", value: "eq" },
    { label: "早于", value: "before" },
    { label: "晚于", value: "after" },
    { label: "为空", value: "empty" },
    { label: "不为空", value: "not_empty" },
  ],
  single_select: [
    { label: "等于", value: "eq" },
    { label: "不等于", value: "ne" },
    { label: "包含", value: "contains" },
    { label: "不包含", value: "not_contains" },
    { label: "为空", value: "empty" },
    { label: "不为空", value: "not_empty" },
  ],
  multi_select: [
    { label: "包含", value: "contains" },
    { label: "不包含", value: "not_contains" },
    { label: "为空", value: "empty" },
    { label: "不为空", value: "not_empty" },
  ],
  images: [
    { label: "为空", value: "empty" },
    { label: "不为空", value: "not_empty" },
  ],
}

const VALUELESS_OPERATORS: FilterOperator[] = ["true", "false", "empty", "not_empty"]

const nextFilterConditionId = () => `filter-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

export const getFilterableColumns = (columns: TradeRecordColumn[]) => columns

export const getFilterOperatorOptions = (column?: TradeRecordColumn | null) => {
  if (!column) {
    return [] as FilterOperatorOption[]
  }
  return OPERATOR_OPTIONS[column.data_type] ?? []
}

export const createDefaultFilterCondition = (columns: TradeRecordColumn[]): FilterCondition => {
  const firstColumn = columns[0]
  const firstOperator = getFilterOperatorOptions(firstColumn)[0]?.value ?? "eq"

  return {
    id: nextFilterConditionId(),
    column_key: firstColumn?.column_key ?? "",
    operator: firstOperator,
    value: getDefaultFilterValue(firstColumn?.data_type, firstOperator),
  }
}

export const getDefaultFilterValue = (
  dataType?: TradeRecordColumn["data_type"],
  operator?: FilterOperator,
) => {
  if (!dataType || !operator || VALUELESS_OPERATORS.includes(operator)) {
    return null
  }

  if (dataType === "number") {
    return null
  }

  if (dataType === "single_select" && (operator === "contains" || operator === "not_contains")) {
    return []
  }

  if (dataType === "multi_select") {
    return []
  }

  return ""
}

const isEmptyValue = (value: unknown) => {
  if (value === null || value === undefined) {
    return true
  }
  if (typeof value === "string") {
    return !value.trim()
  }
  if (Array.isArray(value)) {
    return value.length === 0
  }
  return false
}

const shouldKeepCondition = (condition: FilterCondition, column?: TradeRecordColumn) => {
  if (!column) {
    return false
  }

  const operatorValues = getFilterOperatorOptions(column).map((item) => item.value)
  if (!operatorValues.includes(condition.operator)) {
    return false
  }

  if (VALUELESS_OPERATORS.includes(condition.operator)) {
    return true
  }

  return !isEmptyValue(condition.value)
}

export const normalizeFilterConditions = (
  conditions: FilterCondition[],
  columns: TradeRecordColumn[],
): FilterCondition[] => {
  const columnMap = new Map(columns.map((column) => [column.column_key, column]))

  return conditions
    .map((condition) => {
      const column = columnMap.get(condition.column_key)
      if (!column) {
        return null
      }

      const operatorOptions = getFilterOperatorOptions(column)
      const operatorValues = operatorOptions.map((item) => item.value)
      const operator = operatorValues.includes(condition.operator)
        ? condition.operator
        : operatorOptions[0]?.value ?? "eq"

      const normalizedValue = VALUELESS_OPERATORS.includes(operator)
        ? null
        : normalizeFilterValue(column.data_type, condition.value)

      return {
        id: condition.id || nextFilterConditionId(),
        column_key: column.column_key,
        operator,
        value: normalizedValue,
      } satisfies FilterCondition
    })
    .filter((condition): condition is FilterCondition => Boolean(condition))
}

const normalizeFilterValue = (dataType: TradeRecordColumn["data_type"], value: unknown) => {
  if (dataType === "multi_select") {
    return Array.isArray(value) ? value.map((item) => String(item)) : []
  }

  if (dataType === "single_select" && (Array.isArray(value) || value === null || value === undefined)) {
    return Array.isArray(value) ? value.map((item) => String(item)) : []
  }

  if (dataType === "number") {
    if (value === "" || value === null || value === undefined) {
      return null
    }
    const numericValue = Number(value)
    return Number.isFinite(numericValue) ? numericValue : null
  }

  if (dataType === "bool") {
    return Boolean(value)
  }

  return value === null || value === undefined ? "" : String(value)
}

export const filterTradeRecords = (
  records: TradeRecord[],
  columns: TradeRecordColumn[],
  enabled: boolean,
  logic: FilterLogic,
  conditions: FilterCondition[],
) => {
  const normalizedConditions = normalizeFilterConditions(conditions, columns).filter((condition) =>
    shouldKeepCondition(condition, columns.find((column) => column.column_key === condition.column_key)),
  )

  if (!enabled || !normalizedConditions.length) {
    return records
  }

  const columnMap = new Map(columns.map((column) => [column.column_key, column]))

  return records.filter((record) => {
    const matches = normalizedConditions.map((condition) => {
      const column = columnMap.get(condition.column_key)
      if (!column) {
        return false
      }
      const rowValue = record.data_json[condition.column_key]
      return matchFilterCondition(column, rowValue, condition)
    })

    return logic === "any" ? matches.some(Boolean) : matches.every(Boolean)
  })
}

const matchFilterCondition = (column: TradeRecordColumn, rowValue: unknown, condition: FilterCondition) => {
  if (condition.operator === "empty") {
    return isRecordValueEmpty(column.data_type, rowValue)
  }

  if (condition.operator === "not_empty") {
    return !isRecordValueEmpty(column.data_type, rowValue)
  }

  if (condition.operator === "true") {
    return rowValue === true
  }

  if (condition.operator === "false") {
    return rowValue === false
  }

  if (isRecordValueEmpty(column.data_type, rowValue)) {
    return false
  }

  switch (column.data_type) {
    case "number":
      return compareNumber(rowValue, condition.operator, condition.value)
    case "datetime":
      return compareDateTime(rowValue, condition.operator, condition.value)
    case "multi_select":
      return compareMultiSelect(rowValue, condition.operator, condition.value)
    default:
      return compareString(rowValue, condition.operator, condition.value)
  }
}

const isRecordValueEmpty = (dataType: TradeRecordColumn["data_type"], value: unknown) => {
  if (value === null || value === undefined) {
    return true
  }

  if (dataType === "images" || dataType === "multi_select") {
    return !Array.isArray(value) || value.length === 0
  }

  if (typeof value === "string") {
    return !value.trim()
  }

  return false
}

const compareString = (rowValue: unknown, operator: FilterOperator, targetValue: unknown) => {
  const left = String(rowValue ?? "").trim().toLowerCase()
  const rightValues = Array.isArray(targetValue)
    ? targetValue.map((item) => String(item).trim().toLowerCase()).filter(Boolean)
    : [String(targetValue ?? "").trim().toLowerCase()].filter(Boolean)

  if (!rightValues.length) {
    return false
  }

  if (operator === "eq") {
    return left === rightValues[0]
  }
  if (operator === "ne") {
    return left !== rightValues[0]
  }
  if (operator === "contains") {
    return rightValues.some((item) => left.includes(item))
  }
  if (operator === "not_contains") {
    return rightValues.every((item) => !left.includes(item))
  }
  return false
}

const compareNumber = (rowValue: unknown, operator: FilterOperator, targetValue: unknown) => {
  const left = Number(rowValue)
  const right = Number(targetValue)
  if (!Number.isFinite(left) || !Number.isFinite(right)) {
    return false
  }

  if (operator === "gt") {
    return left > right
  }
  if (operator === "gte") {
    return left >= right
  }
  if (operator === "eq") {
    return left === right
  }
  if (operator === "ne") {
    return left !== right
  }
  if (operator === "lt") {
    return left < right
  }
  if (operator === "lte") {
    return left <= right
  }
  return false
}

const compareDateTime = (rowValue: unknown, operator: FilterOperator, targetValue: unknown) => {
  const left = new Date(String(rowValue)).getTime()
  const right = new Date(String(targetValue)).getTime()
  if (!Number.isFinite(left) || !Number.isFinite(right)) {
    return false
  }

  if (operator === "eq") {
    return left === right
  }
  if (operator === "before") {
    return left < right
  }
  if (operator === "after") {
    return left > right
  }
  return false
}

const compareMultiSelect = (rowValue: unknown, operator: FilterOperator, targetValue: unknown) => {
  if (!Array.isArray(rowValue)) {
    return false
  }

  const rowValues = rowValue.map((item) => String(item))
  const targetValues = Array.isArray(targetValue) ? targetValue.map((item) => String(item)) : [String(targetValue)]

  if (!targetValues.length || targetValues.every((item) => !item.trim())) {
    return false
  }

  if (operator === "contains") {
    return targetValues.some((item) => rowValues.includes(item))
  }
  if (operator === "not_contains") {
    return targetValues.every((item) => !rowValues.includes(item))
  }
  return false
}

export const readTradeRecordManagerViewState = (): TradeRecordManagerViewState | null => {
  if (typeof window === "undefined") {
    return null
  }

  const raw = window.localStorage.getItem(STORAGE_KEY)
  if (!raw) {
    return null
  }

  try {
    const parsed = JSON.parse(raw) as Partial<TradeRecordManagerViewState>
    return {
      sort_enabled: Boolean(parsed.sort_enabled),
      sort_conditions: Array.isArray(parsed.sort_conditions) ? parsed.sort_conditions : [],
      filter_enabled: Boolean(parsed.filter_enabled),
      filter_logic: parsed.filter_logic === "any" ? "any" : "all",
      filter_conditions: Array.isArray(parsed.filter_conditions) ? parsed.filter_conditions : [],
    }
  } catch {
    return null
  }
}

export const saveTradeRecordManagerViewState = (state: TradeRecordManagerViewState) => {
  if (typeof window === "undefined") {
    return
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}
