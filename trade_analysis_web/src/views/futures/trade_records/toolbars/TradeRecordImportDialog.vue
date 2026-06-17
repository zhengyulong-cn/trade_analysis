<script lang="ts" setup>
import { createTradeRecordApi, type TradeAccount, type TradeRecordColumn, type TradeRecordColumnOption } from "@/api/modules"
import { formatDateTime } from "@/utils/date"
import { ElMessage } from "element-plus"
import { computed, ref, watch } from "vue"
import dayjs, { type Dayjs } from 'dayjs'


type ImportRow = Record<string, unknown>

const props = defineProps<{
  modelValue: boolean
  columns: TradeRecordColumn[]
  accounts: TradeAccount[]
}>()

const emit = defineEmits<{
  "update:modelValue": [value: boolean]
  imported: []
}>()

const loading = ref(false)
const rawJson = ref("")
const parsedRows = ref<ImportRow[]>([])

const promptStartTime: Dayjs = dayjs().subtract(1, "day").hour(21).minute(0).second(0).millisecond(0)
const promptEndTime: Dayjs = dayjs().hour(15).minute(0).second(0).millisecond(0)
const importPrompt = `你将从交易软件截图中提取交易记录，并输出为可直接导入系统的 JSON，类型为对象数组，交易时间跨度为${promptStartTime.format("YYYY-MM-DD HH:mm:ss")}至${promptEndTime.format("YYYY-MM-DD HH:mm:ss")}。
对于有平仓匹配不到开仓的不记录，而有开仓匹配不到平仓的则记录，此时平仓相关属性不显示。

合约：contract
品种：product，["氧化铝","焦煤","焦炭","铁矿石","纯碱","玻璃","烧碱","甲醇","乙二醇","PTA","苯乙烯","沥青","塑料","橡胶","合成橡胶","豆一","菜粕","菜油","棕榈油","多晶硅","碳酸锂","鸡蛋","苹果","沪银","沪镍","沪锡"] 中的某一个
账户：3（固定值）
手数：lots，整数
方向：open_direction，多单值为long，空单值为short
开仓时间：open_time，YYYY-MM-DD HH:mm:ss格式
开仓价格：open_price
平仓时间：close_time，YYYY-MM-DD HH:mm:ss格式
平仓价格：close_price

输出示例：
\`\`\`
[
  {
    "contract": "p2609",
    "product": "焦煤",
    "account_id": 3,
    "lots": 10,
    "open_direction": "short"
    "open_time": "2026-06-17 09:31:00",
    "open_price": "1300",
    "close_time": "2026-06-17 10:12:00",
    "close_price": "1250",
  }
]
\`\`\`
`

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit("update:modelValue", value),
})

const enabledColumns = computed(() =>
  [...props.columns]
    .filter((item) => item.is_enabled)
    .sort((a, b) => a.sort_order - b.sort_order || a.column_id - b.column_id),
)

const columnMap = computed(() => {
  const map = new Map<string, TradeRecordColumn>()
  props.columns.forEach((column) => {
    map.set(column.column_key, column)
  })
  return map
})

const previewKeys = computed(() => {
  const importedKeys: string[] = []
  const importedKeySet = new Set<string>()

  parsedRows.value.forEach((row) => {
    Object.keys(row).forEach((key) => {
      if (!importedKeySet.has(key)) {
        importedKeySet.add(key)
        importedKeys.push(key)
      }
    })
  })

  const orderedConfiguredKeys = enabledColumns.value
    .map((column) => column.column_key)
    .filter((key) => importedKeySet.has(key))
  const extraKeys = importedKeys.filter((key) => !orderedConfiguredKeys.includes(key))

  return [...orderedConfiguredKeys, ...extraKeys]
})

const previewColumns = computed(() =>
  previewKeys.value.map((key) => ({
    key,
    column: columnMap.value.get(key) ?? null,
    label: columnMap.value.get(key)?.column_label ?? key,
  })),
)

const getColumnOptions = (column: TradeRecordColumn): TradeRecordColumnOption[] => {
  if (column.option_source_type === "outer") {
    const source = String(column.option_source_config?.source ?? "")
    if (source === "trade_accounts") {
      return props.accounts.map((item) => ({
        label: item.account_name,
        value: String(item.account_id),
      }))
    }
    return []
  }

  return (column.options_json ?? []) as TradeRecordColumnOption[]
}

const getColumnOptionLabel = (column: TradeRecordColumn, value: unknown) => {
  const normalizedValue = String(value ?? "")
  return getColumnOptions(column).find((item) => item.value === normalizedValue)?.label
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

const formatCellValue = (column: TradeRecordColumn | null, value: unknown) => {
  if (value === null || value === undefined || value === "") {
    return "-"
  }

  if (!column) {
    if (Array.isArray(value)) {
      return JSON.stringify(value)
    }
    return String(value)
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

  if (column.data_type === "single_select") {
    return getColumnOptionLabel(column, value) || String(value)
  }

  if (column.data_type === "multi_select") {
    if (!Array.isArray(value)) {
      return String(value)
    }
    return value.map((item) => getColumnOptionLabel(column, item) || String(item)).join("、")
  }

  if (column.data_type === "images") {
    return Array.isArray(value) ? `${value.length} 张` : "-"
  }

  if (Array.isArray(value)) {
    return JSON.stringify(value)
  }

  return String(value)
}

const normalizeImportRows = (input: unknown): ImportRow[] => {
  if (!Array.isArray(input)) {
    throw new Error("JSON 必须是对象数组")
  }

  return input.map((item, index) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) {
      throw new Error(`第 ${index + 1} 条数据不是对象`)
    }
    return JSON.parse(JSON.stringify(item)) as ImportRow
  })
}

const handleParse = () => {
  try {
    const parsed = JSON.parse(rawJson.value) as unknown
    parsedRows.value = normalizeImportRows(parsed)
    ElMessage.success(`已解析 ${parsedRows.value.length} 条记录`)
  } catch (error) {
    parsedRows.value = []
    ElMessage.error(error instanceof Error ? error.message : "JSON 解析失败")
  }
}

const handleCopyPrompt = async () => {
  try {
    await navigator.clipboard.writeText(importPrompt)
    ElMessage.success("提示词已复制")
  } catch {
    ElMessage.error("复制失败，请检查浏览器权限")
  }
}

const handleImport = async () => {
  if (!parsedRows.value.length) {
    ElMessage.warning("请先解析可导入的 JSON 数据")
    return
  }

  loading.value = true
  try {
    for (const row of parsedRows.value) {
      await createTradeRecordApi({ data_json: row })
    }
    ElMessage.success(`成功导入 ${parsedRows.value.length} 条交易记录`)
    visible.value = false
    emit("imported")
  } catch {
    ElMessage.error("导入交易记录失败")
  } finally {
    loading.value = false
  }
}

const resetState = () => {
  rawJson.value = ""
  parsedRows.value = []
}

watch(
  () => props.modelValue,
  (value) => {
    if (!value) {
      resetState()
    }
  },
)
</script>

<template>
  <el-dialog v-model="visible" title="导入交易记录" width="78rem" destroy-on-close>
    <div class="import-layout">
      <div class="input-panel">
        <div class="input-panel-header">
          <div class="panel-title">JSON 输入</div>
          <el-button size="small" @click="handleCopyPrompt">复制提示词</el-button>
        </div>
        <el-input
          v-model="rawJson"
          type="textarea"
          :rows="14"
          resize="none"
          placeholder='例如：[{"contract":"rb2410","open_time":"2026-06-17 09:31:00"}]'
        />
        <div class="panel-actions">
          <el-button @click="handleParse">解析 JSON</el-button>
        </div>
      </div>

      <div class="preview-panel">
        <div class="panel-header">
          <div class="panel-title">导入预览</div>
          <div class="panel-desc">共 {{ parsedRows.length }} 条，确认无误后再写入。</div>
        </div>

        <el-empty v-if="!parsedRows.length" description="暂无预览数据" />

        <el-table v-else :data="parsedRows" border height="26rem" class="preview-table">
          <el-table-column type="index" label="#" width="56" fixed="left" />
          <el-table-column
            v-for="item in previewColumns"
            :key="item.key"
            :label="item.label"
            min-width="160"
            show-overflow-tooltip
          >
            <template #default="{ row }">
              {{ formatCellValue(item.column, row[item.key]) }}
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="loading" @click="handleImport">导入</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped lang="less">
.import-layout {
  display: grid;
  grid-template-columns: minmax(20rem, 24rem) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.input-panel,
.preview-panel {
  background: #f8fafc;
  border: 1px solid #e5eaf3;
  border-radius: 14px;
  padding: 14px;
}

.input-panel-header {
  margin-bottom: 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.panel-header {
  margin-bottom: 12px;
}

.panel-title {
  color: #1a2233;
  font-size: 15px;
  font-weight: 700;
}

.panel-desc {
  margin-top: 4px;
  color: #667085;
  font-size: 12px;
  line-height: 1.5;
}

.panel-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.prompt-box {
  margin-bottom: 12px;
  padding: 12px;
  background: #ffffff;
  border: 1px solid #e5eaf3;
  border-radius: 12px;
}

.prompt-header {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.prompt-title {
  color: #344054;
  font-size: 13px;
  font-weight: 700;
}

.preview-table {
  width: 100%;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 1200px) {
  .import-layout {
    grid-template-columns: 1fr;
  }
}
</style>
