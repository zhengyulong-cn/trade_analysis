<script lang="ts" setup>
import {
  createTradeRecordColumnApi,
  deleteTradeRecordColumnApi,
  updateTradeRecordColumnApi,
  type TradeRecordColumn,
  type TradeRecordColumnDataType,
  type TradeRecordColumnOptionSourceType,
} from "@/api/modules"
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from "element-plus"
import { computed, reactive, ref, watch } from "vue"

interface ColumnConfigForm {
  column_id?: number
  column_key: string
  column_label: string
  data_type: TradeRecordColumnDataType
  table_column_width: number | null
  option_source_type: TradeRecordColumnOptionSourceType
  is_required: boolean
  is_enabled: boolean
  sort_order: number
  options_json_text: string
  option_source_config_text: string
}

const props = defineProps<{
  modelValue: boolean
  columns: TradeRecordColumn[]
}>()

const emit = defineEmits<{
  "update:modelValue": [value: boolean]
  changed: []
}>()

const COLUMN_DATA_TYPE_OPTIONS: Array<{ label: string; value: TradeRecordColumnDataType }> = [
  { label: "布尔", value: "bool" },
  { label: "字符串", value: "string" },
  { label: "数字", value: "number" },
  { label: "日期时间", value: "datetime" },
  { label: "单选", value: "single_select" },
  { label: "多选", value: "multi_select" },
  { label: "图片", value: "images" },
]

const OPTION_SOURCE_OPTIONS: Array<{ label: string; value: TradeRecordColumnOptionSourceType }> = [
  { label: "静态", value: "static" },
  { label: "外部", value: "outer" },
]

const columnSubmitting = ref(false)
const columnFormRef = ref<FormInstance>()
const selectedColumnId = ref<number | null>(null)
const localColumns = ref<TradeRecordColumn[]>([])
const columnForm = reactive<ColumnConfigForm>({
  column_key: "",
  column_label: "",
  data_type: "string",
  table_column_width: null,
  option_source_type: "static",
  is_required: false,
  is_enabled: true,
  sort_order: 0,
  options_json_text: "[]",
  option_source_config_text: "{}",
})

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit("update:modelValue", value),
})

const sortedColumns = computed(() =>
  [...localColumns.value].sort((a, b) => a.sort_order - b.sort_order || a.column_id - b.column_id),
)

const columnEditorTitle = computed(() => (selectedColumnId.value === null ? "新增列" : "编辑列"))
const requiresOptionsJson = computed(() =>
  columnForm.option_source_type === "static" &&
  (columnForm.data_type === "single_select" || columnForm.data_type === "multi_select" || columnForm.data_type === "number"),
)
const requiresSourceConfig = computed(() => columnForm.option_source_type === "outer")

const columnRules = reactive<FormRules<ColumnConfigForm>>({
  column_key: [{ required: true, message: "请输入列标识", trigger: "blur" }],
  column_label: [{ required: true, message: "请输入列名称", trigger: "blur" }],
  data_type: [{ required: true, message: "请选择字段类型", trigger: "change" }],
})

watch(
  () => props.columns,
  (value) => {
    localColumns.value = [...value]
  },
  { immediate: true },
)

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      resetColumnForm()
    }
  },
)

const resetColumnForm = () => {
  selectedColumnId.value = null
  columnForm.column_id = undefined
  columnForm.column_key = ""
  columnForm.column_label = ""
  columnForm.data_type = "string"
  columnForm.table_column_width = null
  columnForm.option_source_type = "static"
  columnForm.is_required = false
  columnForm.is_enabled = true
  columnForm.sort_order = sortedColumns.value.length + 1
  columnForm.options_json_text = "[]"
  columnForm.option_source_config_text = "{}"
  columnFormRef.value?.clearValidate()
}

const editColumn = (column?: TradeRecordColumn | null) => {
  if (!column) {
    return
  }

  selectedColumnId.value = column.column_id
  columnForm.column_id = column.column_id
  columnForm.column_key = column.column_key
  columnForm.column_label = column.column_label
  columnForm.data_type = column.data_type
  columnForm.table_column_width = column.table_column_width
  columnForm.option_source_type = column.option_source_type
  columnForm.is_required = column.is_required
  columnForm.is_enabled = column.is_enabled
  columnForm.sort_order = column.sort_order
  columnForm.options_json_text = JSON.stringify(column.options_json ?? [], null, 2)
  columnForm.option_source_config_text = JSON.stringify(column.option_source_config ?? {}, null, 2)
  columnFormRef.value?.clearValidate()
}

const parseJsonText = (text: string, fallback: unknown) => {
  const trimmed = text.trim()
  if (!trimmed) {
    return fallback
  }
  return JSON.parse(trimmed)
}

const buildColumnPayload = () => {
  const optionsJson = parseJsonText(columnForm.options_json_text, [])
  const sourceConfig = parseJsonText(columnForm.option_source_config_text, {})

  if (!Array.isArray(optionsJson)) {
    throw new Error("options_json 必须是数组")
  }

  if (sourceConfig === null || Array.isArray(sourceConfig) || typeof sourceConfig !== "object") {
    throw new Error("option_source_config 必须是对象")
  }

  return {
    column_key: columnForm.column_key.trim(),
    column_label: columnForm.column_label.trim(),
    data_type: columnForm.data_type,
    table_column_width: columnForm.table_column_width,
    option_source_type: columnForm.option_source_type,
    is_required: columnForm.is_required,
    is_enabled: columnForm.is_enabled,
    sort_order: columnForm.sort_order,
    options_json: optionsJson as Array<Record<string, unknown>>,
    option_source_config: sourceConfig as Record<string, unknown>,
  }
}

const createDefaultColumn = async () => {
  columnSubmitting.value = true
  try {
    const created = await createTradeRecordColumnApi({
      column_key: "new_identifier",
      column_label: "new_column",
      data_type: "string",
      table_column_width: 120,
      option_source_type: "static",
      is_required: false,
      is_enabled: false,
      sort_order: 999,
      options_json: [],
      option_source_config: {},
    })
    localColumns.value = [...localColumns.value, created]
    ElMessage.success("已创建新的列配置")
    editColumn(created)
    emit("changed")
  } catch {
    ElMessage.error("创建新的列配置失败")
  } finally {
    columnSubmitting.value = false
  }
}

const submitColumnForm = async () => {
  if (!columnFormRef.value) {
    return
  }

  const valid = await columnFormRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }

  columnSubmitting.value = true
  try {
    const payload = buildColumnPayload()
    if (selectedColumnId.value === null) {
      const created = await createTradeRecordColumnApi(payload)
      localColumns.value = [...localColumns.value, created]
      selectedColumnId.value = created.column_id
      ElMessage.success("列已创建")
    } else {
      const updated = await updateTradeRecordColumnApi({
        column_id: selectedColumnId.value,
        ...payload,
      })
      localColumns.value = localColumns.value.map((item) =>
        item.column_id === updated.column_id ? updated : item,
      )
      editColumn(updated)
      ElMessage.success("列已更新")
    }

    emit("changed")
  } catch (error) {
    const message = error instanceof Error ? error.message : "保存列配置失败"
    ElMessage.error(message)
  } finally {
    columnSubmitting.value = false
  }
}

const handleDeleteColumn = async (column: TradeRecordColumn) => {
  try {
    await ElMessageBox.confirm(`确认删除列【${column.column_label}】吗？`, "删除列配置", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    })
  } catch {
    return
  }

  try {
    await deleteTradeRecordColumnApi(column.column_id)
    localColumns.value = localColumns.value.filter((item) => item.column_id !== column.column_id)
    if (selectedColumnId.value === column.column_id) {
      resetColumnForm()
    }
    ElMessage.success("列已删除")
    emit("changed")
  } catch {
    ElMessage.error("删除列配置失败")
  }
}

const handleClosed = () => {
  resetColumnForm()
}
</script>

<template>
  <el-dialog v-model="dialogVisible" title="列配置" width="1360px" destroy-on-close @closed="handleClosed">
    <div class="column-config-layout">
      <div class="column-config-list">
        <div class="list-header">
          <div class="section-title">已有列</div>
          <el-button size="small" :loading="columnSubmitting" @click="createDefaultColumn">新增列配置</el-button>
        </div>
        <el-table :data="sortedColumns" border height="520" highlight-current-row @current-change="editColumn">
          <el-table-column prop="column_label" label="列名" min-width="120" />
          <el-table-column prop="column_key" label="Key" min-width="140" />
          <el-table-column prop="data_type" label="类型" width="110" />
          <el-table-column prop="sort_order" label="排序" width="80" />
          <el-table-column prop="table_column_width" label="宽度" width="80" />
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button link type="danger" @click.stop="handleDeleteColumn(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="column-config-editor">
        <div class="editor-header">
          <div class="section-title">{{ columnEditorTitle }}</div>
          <el-button text @click="resetColumnForm">重置</el-button>
        </div>

        <el-form ref="columnFormRef" :model="columnForm" :rules="columnRules" label-position="top" class="column-form">
          <div class="column-form-grid">
            <el-form-item label="列标识" prop="column_key">
              <el-input v-model="columnForm.column_key" placeholder="例如：open_price" />
            </el-form-item>

            <el-form-item label="列名称" prop="column_label">
              <el-input v-model="columnForm.column_label" placeholder="例如：开仓价格" />
            </el-form-item>

            <el-form-item label="字段类型" prop="data_type">
              <el-select v-model="columnForm.data_type" class="full-width">
                <el-option
                  v-for="option in COLUMN_DATA_TYPE_OPTIONS"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="选项来源">
              <el-select v-model="columnForm.option_source_type" class="full-width">
                <el-option
                  v-for="option in OPTION_SOURCE_OPTIONS"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="表格列宽">
              <el-input-number v-model="columnForm.table_column_width" :min="0" :step="10" class="full-width" />
            </el-form-item>

            <el-form-item label="排序">
              <el-input-number v-model="columnForm.sort_order" :min="0" :step="1" class="full-width" />
            </el-form-item>

            <el-form-item>
              <template #label>必填</template>
              <el-switch v-model="columnForm.is_required" />
            </el-form-item>

            <el-form-item>
              <template #label>启用</template>
              <el-switch v-model="columnForm.is_enabled" />
            </el-form-item>

            <el-form-item v-if="requiresOptionsJson" label="options_json" class="full-row">
              <el-input
                v-model="columnForm.options_json_text"
                type="textarea"
                :rows="8"
                placeholder='例如：[{"label":"趋势推动段","value":"trend_push"}] 或 [{"precision":2}]'
              />
            </el-form-item>

            <el-form-item v-if="requiresSourceConfig" label="option_source_config" class="full-row">
              <el-input
                v-model="columnForm.option_source_config_text"
                type="textarea"
                :rows="6"
                placeholder='例如：{"source":"trade_accounts"}'
              />
            </el-form-item>
          </div>
        </el-form>

        <div class="dialog-footer">
          <el-button @click="resetColumnForm">清空</el-button>
          <el-button type="primary" :loading="columnSubmitting" @click="submitColumnForm">保存列配置</el-button>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped lang="less">
.column-config-layout {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 20px;
  align-items: start;
}

.column-config-list,
.column-config-editor {
  min-width: 0;
}

.column-config-list {
  padding-right: 4px;
}

.column-config-editor {
  padding-left: 4px;
  border-left: 1px solid #ebeef5;
}

.list-header,
.editor-header,
.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.list-header {
  margin-bottom: 12px;
}

.dialog-footer {
  justify-content: flex-end;
}

.section-title {
  color: #1a2233;
  font-size: 16px;
  font-weight: 700;
}

.column-form {
  padding-top: 4px;
}

.column-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.full-row {
  grid-column: 1 / -1;
}

.full-width {
  width: 100%;
}

@media (max-width: 1280px) {
  .column-config-layout {
    grid-template-columns: 1fr;
  }

  .column-config-editor {
    padding-left: 0;
    border-left: none;
    border-top: 1px solid #ebeef5;
    padding-top: 20px;
  }
}

@media (max-width: 900px) {
  .column-form-grid {
    grid-template-columns: 1fr;
  }

  .full-row {
    grid-column: auto;
  }
}
</style>
