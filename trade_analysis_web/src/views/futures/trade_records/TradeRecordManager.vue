<script lang="ts" setup>
import {
  deleteTradeRecordApi,
  getTradeAccountListApi,
  getTradeRecordColumnListApi,
  getTradeRecordListApi,
  resolveTradeRecordImageUrl,
  type TradeAccount,
  type TradeRecord,
  type TradeRecordColumn,
  type TradeRecordColumnOption,
  type TradeRecordImage,
} from "@/api/modules"
import { formatDateTime } from "@/utils/date"
import TradeRecordColumnConfigDialog from "./TradeRecordColumnConfigDialog.vue"
import TradeRecordFormDialog from "./TradeRecordFormDialog.vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { computed, onMounted, ref } from "vue"

type DialogMode = "create" | "edit"

const DEFAULT_TABLE_MIN_WIDTH = 160

const loading = ref(false)
const dialogVisible = ref(false)
const columnDialogVisible = ref(false)
const dialogMode = ref<DialogMode>("create")
const editingRecord = ref<TradeRecord | null>(null)
const columns = ref<TradeRecordColumn[]>([])
const accounts = ref<TradeAccount[]>([])
const records = ref<TradeRecord[]>([])

defineProps<{
  handleModeChange: (mode: string | number | boolean) => void
}>()

const enabledColumns = computed(() =>
  [...columns.value]
    .filter((item) => item.is_enabled)
    .sort((a, b) => a.sort_order - b.sort_order || a.column_id - b.column_id),
)

const getColumnOptions = (column: TradeRecordColumn): TradeRecordColumnOption[] => {
  if (column.option_source_type === "outer") {
    const source = String(column.option_source_config?.source ?? "")
    if (source === "trade_accounts") {
      return accounts.value.map((item) => ({
        label: item.account_name,
        value: String(item.account_id),
      }))
    }
    return []
  }

  return (column.options_json ?? []) as TradeRecordColumnOption[]
}

const getColumnOptionMeta = (column: TradeRecordColumn, value: unknown) => {
  const normalizedValue = String(value ?? "")
  return getColumnOptions(column).find((item) => item.value === normalizedValue)
}

const getTagProps = (option?: TradeRecordColumnOption) => ({
  type: option?.tag_type || "info",
  effect: option?.effect || "dark",
})

const getTagStyle = (option?: TradeRecordColumnOption) => {
  if (!option?.color && !option?.text_color && !option?.border_color) {
    return undefined
  }

  return {
    backgroundColor: option.color || undefined,
    borderColor: option.border_color || option.color || undefined,
    color: option.text_color || undefined,
  }
}

const getNumberPrecision = (column: TradeRecordColumn) => {
  const option = Array.isArray(column.options_json) ? column.options_json[0] : undefined
  const precision = option && "precision" in option ? Number((option as Record<string, unknown>).precision) : NaN
  if (Number.isFinite(precision) && precision >= 0) {
    return precision
  }
  return 2
}

const formatNumberCellValue = (column: TradeRecordColumn, value: unknown) => {
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) {
    return String(value)
  }
  return numericValue.toFixed(getNumberPrecision(column))
}

const formatCellValue = (column: TradeRecordColumn, value: unknown) => {
  if (value === null || value === undefined || value === "") {
    return "-"
  }

  if (column.data_type === "datetime") {
    return formatDateTime(String(value))
  }

  if (column.data_type === "number") {
    return formatNumberCellValue(column, value)
  }

  if (column.data_type === "bool") {
    return value ? "是" : "否"
  }

  if (column.data_type === "images") {
    return Array.isArray(value) ? `${value.length} 张` : "-"
  }

  return String(value)
}

const loadPageData = async () => {
  loading.value = true
  try {
    const [columnList, accountList, recordList] = await Promise.all([
      getTradeRecordColumnListApi(),
      getTradeAccountListApi(),
      getTradeRecordListApi(),
    ])
    columns.value = columnList
    accounts.value = accountList
    records.value = recordList
  } catch {
    ElMessage.error("交易记录页面数据加载失败")
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  dialogMode.value = "create"
  editingRecord.value = null
  dialogVisible.value = true
}

const openEditDialog = (record: TradeRecord) => {
  dialogMode.value = "edit"
  editingRecord.value = record
  dialogVisible.value = true
}

const openColumnDialog = () => {
  columnDialogVisible.value = true
}

const handleFormSaved = async () => {
  editingRecord.value = null
  await loadPageData()
}

const handleDelete = async (record: TradeRecord) => {
  try {
    await ElMessageBox.confirm("删除后无法恢复，确认继续吗？", "删除交易记录", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    })
  } catch {
    return
  }

  try {
    await deleteTradeRecordApi(record.trade_record_id)
    ElMessage.success("交易记录已删除")
    await loadPageData()
  } catch {
    ElMessage.error("删除交易记录失败")
  }
}

onMounted(async () => {
  await loadPageData()
})
</script>

<template>
  <section class="trade-record-page">
    <div class="manager-card">
      <header class="toolbar">
        <div class="toolbar-left">
          <div class="toolbar-title">
            交易记录
            <el-icon class="icon" @click="handleModeChange('analysis')">
              <Switch />
            </el-icon>
          </div>
        </div>
        <div class="toolbar-right">
          <div class="summary">{{ records.length }} 条记录</div>
          <el-button @click="loadPageData">刷新</el-button>
          <el-button type="primary" @click="openCreateDialog">新增交易记录</el-button>
          <el-button type="warning" @click="openColumnDialog">列配置</el-button>
        </div>
      </header>

      <el-empty v-if="!loading && !records.length" description="暂无交易记录" />

      <el-table v-else v-loading="loading" :data="records" border stripe class="record-table" height="45rem">
        <el-table-column prop="trade_record_id" label="ID" width="60" fixed="left" />
        <el-table-column
          v-for="column in enabledColumns"
          :key="column.column_id"
          :label="column.column_label"
          :width="column.table_column_width || undefined"
          :min-width="column.table_column_width ? undefined : DEFAULT_TABLE_MIN_WIDTH"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <template v-if="column.data_type === 'images'">
              <div
                v-if="Array.isArray(row.data_json[column.column_key]) && row.data_json[column.column_key].length"
                class="image-list"
              >
                <el-image
                  v-for="item in row.data_json[column.column_key]"
                  :key="item.path"
                  :src="resolveTradeRecordImageUrl(item.path)"
                  :preview-src-list="
                    row.data_json[column.column_key].map((image: TradeRecordImage) => resolveTradeRecordImageUrl(image.path))
                  "
                  class="image-thumb"
                  fit="cover"
                  preview-teleported
                />
              </div>
              <span v-else>-</span>
            </template>
            <template
              v-else-if="
                column.data_type === 'single_select' &&
                row.data_json[column.column_key] !== null &&
                row.data_json[column.column_key] !== undefined &&
                row.data_json[column.column_key] !== ''
              "
            >
              <el-tag
                v-if="getColumnOptionMeta(column, row.data_json[column.column_key])"
                size="small"
                class="record-tag"
                v-bind="getTagProps(getColumnOptionMeta(column, row.data_json[column.column_key]))"
                :style="getTagStyle(getColumnOptionMeta(column, row.data_json[column.column_key]))"
                round
              >
                {{ getColumnOptionMeta(column, row.data_json[column.column_key])?.label }}
              </el-tag>
              <span v-else>{{ String(row.data_json[column.column_key]) }}</span>
            </template>
            <template v-else-if="column.data_type === 'multi_select'">
              <div
                v-if="Array.isArray(row.data_json[column.column_key]) && row.data_json[column.column_key].length"
                class="tag-list"
              >
                <template v-for="item in row.data_json[column.column_key]" :key="String(item)">
                  <el-tag
                    v-if="getColumnOptionMeta(column, item)"
                    size="small"
                    class="record-tag"
                    v-bind="getTagProps(getColumnOptionMeta(column, item))"
                    :style="getTagStyle(getColumnOptionMeta(column, item))"
                    round
                  >
                    {{ getColumnOptionMeta(column, item)?.label }}
                  </el-tag>
                  <span v-else class="tag-fallback">{{ String(item) }}</span>
                </template>
              </div>
              <span v-else>-</span>
            </template>
            <template v-else>
              {{ formatCellValue(column, row.data_json[column.column_key]) }}
            </template>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <TradeRecordFormDialog
      v-model="dialogVisible"
      :mode="dialogMode"
      :record="editingRecord"
      :columns="columns"
      :accounts="accounts"
      @saved="handleFormSaved"
    />

    <TradeRecordColumnConfigDialog v-model="columnDialogVisible" :columns="columns" @changed="loadPageData" />
  </section>
</template>

<style scoped lang="less">
.trade-record-page {
  padding: 16px;
}

.manager-card {
  display: flex;
  flex-direction: column;
  row-gap: 12px;
}

.toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.toolbar-left {
  min-width: 0;
}

.toolbar-title {
  display: flex;
  align-items: center;
  column-gap: 4px;
  color: #1a2233;
  font-size: 20px;
  font-weight: 700;
}

.icon {
  cursor: pointer;

  &:hover {
    color: #409eff;
  }
}

.toolbar-right {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.summary {
  color: #5f6b7c;
  font-size: 13px;
  white-space: nowrap;
  margin-right: 12px;
}

.record-table {
  width: 100%;
}

.image-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.image-thumb {
  width: 52px;
  height: 52px;
  overflow: hidden;
  border-radius: 10px;
  background: #f3f5f9;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.record-tag {
  margin: 2px 0;
  border-width: 1px;
  border-style: solid;
}

.tag-fallback {
  color: #445066;
  font-size: 13px;
}

@media (max-width: 900px) {
  .toolbar {
    flex-direction: column;
  }

  .toolbar-right {
    width: 100%;
  }
}
</style>
