<script lang="ts" setup>
import {
  deleteOpportunityReviewApi,
  getOpportunityReviewColumnListApi,
  getOpportunityReviewListApi,
  resolveStorageImageUrl,
  type OpportunityReview,
  type OpportunityReviewColumn,
  type OpportunityReviewColumnOption,
  type ImageAttachment,
} from "@/api/modules"
import { formatDateTime } from "@/utils/date"
import { ElMessage, ElMessageBox } from "element-plus"
import { computed, onMounted, ref } from "vue"
import OpportunityReviewColumnConfigDialog from "./OpportunityReviewColumnConfigDialog.vue"
import OpportunityReviewFormDialog from "./OpportunityReviewFormDialog.vue"

type DialogMode = "create" | "edit"

const DEFAULT_TABLE_MIN_WIDTH = 160

const loading = ref(false)
const dialogVisible = ref(false)
const columnDialogVisible = ref(false)
const dialogMode = ref<DialogMode>("create")
const editingRecord = ref<OpportunityReview | null>(null)
const columns = ref<OpportunityReviewColumn[]>([])
const records = ref<OpportunityReview[]>([])

const enabledColumns = computed(() =>
  [...columns.value]
    .filter((item) => item.is_enabled)
    .sort((a, b) => a.sort_order - b.sort_order || a.column_id - b.column_id),
)

const getColumnOptions = (column: OpportunityReviewColumn): OpportunityReviewColumnOption[] =>
  (column.options_json ?? []) as OpportunityReviewColumnOption[]

const getColumnOptionMeta = (column: OpportunityReviewColumn, value: unknown) => {
  const normalizedValue = String(value ?? "")
  return getColumnOptions(column).find((item) => item.value === normalizedValue)
}

const getTagProps = (option?: OpportunityReviewColumnOption) => ({
  type: option?.tag_type || "info",
  effect: option?.effect || "dark",
})

const getTagStyle = (option?: OpportunityReviewColumnOption) => {
  if (!option?.color && !option?.text_color && !option?.border_color) {
    return undefined
  }

  return {
    backgroundColor: option.color || undefined,
    borderColor: option.border_color || option.color || undefined,
    color: option.text_color || undefined,
  }
}

const getNumberDisplayOption = (column: OpportunityReviewColumn) => {
  const option = Array.isArray(column.options_json) ? column.options_json[0] : undefined
  return option && typeof option === "object" ? (option as Record<string, unknown>) : {}
}

const getNumberPrecision = (column: OpportunityReviewColumn) => {
  const option = getNumberDisplayOption(column)
  const precision = option && "precision" in option ? Number((option as Record<string, unknown>).precision) : NaN
  if (Number.isFinite(precision) && precision >= 0) {
    return precision
  }
  return 2
}

const formatNumberCellValue = (column: OpportunityReviewColumn, value: unknown) => {
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) {
    return String(value)
  }
  const option = getNumberDisplayOption(column)
  const prefix = typeof option.prefix === "string" ? option.prefix : ""
  const suffix = typeof option.suffix === "string" ? option.suffix : ""
  return `${prefix}${numericValue.toFixed(getNumberPrecision(column))}${suffix}`
}

const formatCellValue = (column: OpportunityReviewColumn, value: unknown) => {
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
    const [columnList, recordList] = await Promise.all([
      getOpportunityReviewColumnListApi(),
      getOpportunityReviewListApi(),
    ])
    columns.value = columnList
    records.value = recordList
  } catch {
    ElMessage.error("机会回顾页面数据加载失败")
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  dialogMode.value = "create"
  editingRecord.value = null
  dialogVisible.value = true
}

const openEditDialog = (record: OpportunityReview) => {
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

const handleDelete = async (record: OpportunityReview) => {
  try {
    await ElMessageBox.confirm("删除后无法恢复，确认继续吗？", "删除机会回顾记录", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    })
  } catch {
    return
  }

  try {
    await deleteOpportunityReviewApi(record.opportunity_review_id)
    ElMessage.success("机会回顾记录已删除")
    await loadPageData()
  } catch {
    ElMessage.error("删除机会回顾记录失败")
  }
}

onMounted(loadPageData)
</script>

<template>
  <section class="opportunity-review-page">
    <div class="manager-card">
      <header class="toolbar">
        <div class="toolbar-left">
          <div class="toolbar-title">机会回顾</div>
          <div class="toolbar-subtitle">记录历史行情里值得复盘的交易机会</div>
        </div>
        <div class="toolbar-right">
          <div class="summary">{{ records.length }} 条记录</div>
          <el-button @click="loadPageData">刷新</el-button>
          <el-button type="primary" @click="openCreateDialog">新增机会回顾记录</el-button>
          <el-button type="warning" @click="openColumnDialog">列配置</el-button>
        </div>
      </header>

      <el-empty v-if="!loading && !records.length" description="暂无机会回顾记录" />

      <el-table v-else v-loading="loading" :data="records" border stripe class="review-table" height="45rem">
        <el-table-column prop="opportunity_review_id" label="ID" width="70" fixed="left" />
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
                  :src="resolveStorageImageUrl(item.path)"
                  :preview-src-list="
                    row.data_json[column.column_key].map((image: ImageAttachment) => resolveStorageImageUrl(image.path))
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
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <OpportunityReviewFormDialog
      v-model="dialogVisible"
      :mode="dialogMode"
      :record="editingRecord"
      :columns="columns"
      @saved="handleFormSaved"
    />

    <OpportunityReviewColumnConfigDialog v-model="columnDialogVisible" :columns="columns" @changed="loadPageData" />
  </section>
</template>

<style scoped lang="less">
.opportunity-review-page {
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
  color: #1a2233;
  font-size: 20px;
  font-weight: 700;
}

.toolbar-subtitle {
  margin-top: 4px;
  color: #7d8899;
  font-size: 13px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.summary {
  color: #5f6b7c;
  font-size: 13px;
  white-space: nowrap;
}

.review-table {
  width: 100%;
}

.image-list,
.tag-list {
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
