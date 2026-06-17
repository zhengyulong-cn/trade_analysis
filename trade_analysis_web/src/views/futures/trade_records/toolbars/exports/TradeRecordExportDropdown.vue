<script setup lang="ts">
import type { TradeRecord, TradeRecordColumn, TradeRecordColumnOption } from "@/api/modules"
import { ElMessage } from "element-plus"
import { exportTradeRecordsToExcel } from "./tradeRecordExcelExport"

type ExportCommand = "excel" | "markdown" | "pdf"

const props = defineProps<{
  records: TradeRecord[]
  columns: TradeRecordColumn[]
  getColumnOptions: (column: TradeRecordColumn) => TradeRecordColumnOption[]
}>()

const handleCommand = (command: ExportCommand) => {
  if (command === "excel") {
    if (!props.records.length) {
      ElMessage.warning("当前没有可导出的交易记录")
      return
    }

    exportTradeRecordsToExcel(props.records, props.columns, props.getColumnOptions)
    ElMessage.success("交易记录已导出")
    return
  }

  ElMessage.info("该导出格式暂未实现")
}
</script>

<template>
  <el-dropdown trigger="click" @command="handleCommand">
    <el-button>
      导出
      <el-icon class="el-icon--right">
        <ArrowDown />
      </el-icon>
    </el-button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item command="excel">导出Excel</el-dropdown-item>
        <el-dropdown-item command="markdown" disabled>导出Markdown</el-dropdown-item>
        <el-dropdown-item command="pdf" disabled>导出PDF</el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>
