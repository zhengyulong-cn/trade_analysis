import type { TradeRecord, TradeRecordColumn, TradeRecordColumnOption, TradeRecordImage } from "@/api/modules"
import { formatDateTime } from "@/utils/date"
import { saveAs } from "file-saver"
import * as XLSX from "xlsx"

type GetColumnOptions = (column: TradeRecordColumn) => TradeRecordColumnOption[]

const getTimestamp = () => {
  const date = new Date()
  const pad = (value: number) => String(value).padStart(2, "0")
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}_${pad(date.getHours())}${pad(
    date.getMinutes(),
  )}${pad(date.getSeconds())}`
}

const getNumberDisplayOption = (column: TradeRecordColumn) => {
  const option = Array.isArray(column.options_json) ? column.options_json[0] : undefined
  return option && typeof option === "object" ? (option as Record<string, unknown>) : {}
}

const getNumberPrecision = (column: TradeRecordColumn) => {
  const option = getNumberDisplayOption(column)
  const precision = option && "precision" in option ? Number(option.precision) : NaN
  if (Number.isFinite(precision) && precision >= 0) {
    return precision
  }
  return 2
}

const formatNumberValue = (column: TradeRecordColumn, value: unknown) => {
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) {
    return String(value)
  }

  const option = getNumberDisplayOption(column)
  const prefix = typeof option.prefix === "string" ? option.prefix : ""
  const suffix = typeof option.suffix === "string" ? option.suffix : ""
  return `${prefix}${numericValue.toFixed(getNumberPrecision(column))}${suffix}`
}

const getOptionLabel = (column: TradeRecordColumn, value: unknown, getColumnOptions: GetColumnOptions) => {
  const normalizedValue = String(value ?? "")
  return getColumnOptions(column).find((item) => item.value === normalizedValue)?.label
}

const formatExportValue = (
  column: TradeRecordColumn,
  value: unknown,
  getColumnOptions: GetColumnOptions,
) => {
  if (value === null || value === undefined || value === "") {
    return ""
  }

  if (column.data_type === "images") {
    if (!Array.isArray(value)) {
      return ""
    }
    return value
      .map((item) => {
        const image = item as Partial<TradeRecordImage>
        return image.original_name || image.path || ""
      })
      .filter(Boolean)
      .join("\n")
  }

  if (column.data_type === "single_select") {
    return getOptionLabel(column, value, getColumnOptions) || String(value)
  }

  if (column.data_type === "multi_select") {
    if (!Array.isArray(value)) {
      return ""
    }
    return value.map((item) => getOptionLabel(column, item, getColumnOptions) || String(item)).join("、")
  }

  if (column.data_type === "datetime") {
    return formatDateTime(String(value))
  }

  if (column.data_type === "number") {
    return formatNumberValue(column, value)
  }

  if (column.data_type === "bool") {
    return value ? "是" : "否"
  }

  return String(value)
}

export const exportTradeRecordsToExcel = (
  records: TradeRecord[],
  columns: TradeRecordColumn[],
  getColumnOptions: GetColumnOptions,
) => {
  const rows = records.map((record) => [
    record.trade_record_id,
    ...columns.map((column) => formatExportValue(column, record.data_json[column.column_key], getColumnOptions)),
  ])
  const worksheet = XLSX.utils.aoa_to_sheet([["ID", ...columns.map((column) => column.column_label)], ...rows])
  const workbook = XLSX.utils.book_new()

  XLSX.utils.book_append_sheet(workbook, worksheet, "交易记录")

  const excelBuffer = XLSX.write(workbook, {
    bookType: "xlsx",
    type: "array",
  })
  const blob = new Blob([excelBuffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;charset=UTF-8",
  })

  saveAs(blob, `交易记录_${getTimestamp()}.xlsx`)
}
