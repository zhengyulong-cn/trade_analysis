<script lang="ts" setup>
import {
  createOpportunityReviewColumnApi,
  deleteOpportunityReviewColumnApi,
  updateOpportunityReviewColumnApi,
  type OpportunityReviewColumn,
  type OpportunityReviewColumnDataType,
} from "@/api/modules"
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from "element-plus"
import { computed, reactive, ref, watch } from "vue"

interface ColumnForm {
  column_id?: number
  column_key: string
  column_label: string
  data_type: OpportunityReviewColumnDataType
  table_column_width: number | null
  is_required: boolean
  is_enabled: boolean
  sort_order: number
  options_json_text: string
}

const props = defineProps<{
  modelValue: boolean
  columns: OpportunityReviewColumn[]
}>()

const emit = defineEmits<{
  "update:modelValue": [value: boolean]
  changed: []
}>()

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit("update:modelValue", value),
})

const localColumns = ref<OpportunityReviewColumn[]>([])
const selectedColumnId = ref<number | null>(null)
const submitting = ref(false)
const formRef = ref<FormInstance>()

const columnForm = reactive<ColumnForm>({
  column_key: "",
  column_label: "",
  data_type: "string",
  table_column_width: 120,
  is_required: false,
  is_enabled: true,
  sort_order: 999,
  options_json_text: "[]",
})

const rules = reactive<FormRules<ColumnForm>>({
  column_key: [{ required: true, message: "请输入列标识", trigger: "blur" }],
  column_label: [{ required: true, message: "请输入列名称", trigger: "blur" }],
  data_type: [{ required: true, message: "请选择字段类型", trigger: "change" }],
})

const sortedColumns = computed(() =>
  [...localColumns.value].sort((a, b) => a.sort_order - b.sort_order || a.column_id - b.column_id),
)

const editorTitle = computed(() => (selectedColumnId.value === null ? "新增列配置" : "编辑列配置"))
const isImagesColumn = computed(() => columnForm.data_type === "images")

watch(
  () => props.columns,
  (value) => {
    localColumns.value = [...value]
    if (selectedColumnId.value && !value.some((item) => item.column_id === selectedColumnId.value)) {
      resetForm()
    }
  },
  { immediate: true },
)

const resetForm = () => {
  selectedColumnId.value = null
  columnForm.column_id = undefined
  columnForm.column_key = ""
  columnForm.column_label = ""
  columnForm.data_type = "string"
  columnForm.table_column_width = 120
  columnForm.is_required = false
  columnForm.is_enabled = true
  columnForm.sort_order = 999
  columnForm.options_json_text = "[]"
  formRef.value?.clearValidate()
}

const editColumn = (column?: OpportunityReviewColumn | null) => {
  if (!column) {
    resetForm()
    return
  }

  selectedColumnId.value = column.column_id
  columnForm.column_id = column.column_id
  columnForm.column_key = column.column_key
  columnForm.column_label = column.column_label
  columnForm.data_type = column.data_type
  columnForm.table_column_width = column.table_column_width
  columnForm.is_required = column.is_required
  columnForm.is_enabled = column.is_enabled
  columnForm.sort_order = column.sort_order
  columnForm.options_json_text = JSON.stringify(column.options_json ?? [], null, 2)
  formRef.value?.clearValidate()
}

const parseOptions = () => {
  if (isImagesColumn.value) {
    return []
  }

  try {
    const parsed = JSON.parse(columnForm.options_json_text || "[]")
    if (!Array.isArray(parsed)) {
      throw new Error("options_json 必须是数组")
    }
    return parsed as Array<Record<string, unknown>>
  } catch (error) {
    const message = error instanceof Error ? error.message : "options_json 解析失败"
    throw new Error(message)
  }
}

const createDefaultColumn = async () => {
  submitting.value = true
  try {
    const created = await createOpportunityReviewColumnApi({
      column_key: "new_identifier",
      column_label: "new_column",
      data_type: "string",
      table_column_width: 120,
      is_required: false,
      is_enabled: false,
      sort_order: 999,
      options_json: [],
    })
    localColumns.value = [...localColumns.value, created]
    editColumn(created)
    ElMessage.success("已创建新的列配置")
    emit("changed")
  } catch {
    ElMessage.error("创建新的列配置失败")
  } finally {
    submitting.value = false
  }
}

const submitForm = async () => {
  if (!formRef.value) {
    return
  }

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }

  let optionsJson: Array<Record<string, unknown>>
  try {
    optionsJson = parseOptions()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "options_json 解析失败")
    return
  }

  submitting.value = true
  try {
    if (selectedColumnId.value === null) {
      const created = await createOpportunityReviewColumnApi({
        column_key: columnForm.column_key.trim(),
        column_label: columnForm.column_label.trim(),
        data_type: columnForm.data_type,
        table_column_width: columnForm.table_column_width,
        is_required: columnForm.is_required,
        is_enabled: columnForm.is_enabled,
        sort_order: columnForm.sort_order,
        options_json: optionsJson,
      })
      localColumns.value = [...localColumns.value, created]
      editColumn(created)
      ElMessage.success("列配置已创建")
    } else {
      const updated = await updateOpportunityReviewColumnApi({
        column_id: selectedColumnId.value,
        column_key: columnForm.column_key.trim(),
        column_label: columnForm.column_label.trim(),
        data_type: columnForm.data_type,
        table_column_width: columnForm.table_column_width,
        is_required: columnForm.is_required,
        is_enabled: columnForm.is_enabled,
        sort_order: columnForm.sort_order,
        options_json: optionsJson,
      })
      localColumns.value = localColumns.value.map((item) => (item.column_id === updated.column_id ? updated : item))
      ElMessage.success("列配置已更新")
    }

    emit("changed")
  } catch {
    ElMessage.error("保存列配置失败")
  } finally {
    submitting.value = false
  }
}

const handleDeleteColumn = async (column: OpportunityReviewColumn) => {
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
    await deleteOpportunityReviewColumnApi(column.column_id)
    localColumns.value = localColumns.value.filter((item) => item.column_id !== column.column_id)
    if (selectedColumnId.value === column.column_id) {
      resetForm()
    }
    ElMessage.success("列配置已删除")
    emit("changed")
  } catch {
    ElMessage.error("删除列配置失败")
  }
}

const handleClosed = () => {
  resetForm()
}
</script>

<template>
  <el-dialog v-model="dialogVisible" title="机会回顾列配置" width="1320px" destroy-on-close @closed="handleClosed">
    <div class="column-config-layout">
      <div class="column-list">
        <div class="section-head">
          <div class="section-title">已有列</div>
          <el-button size="small" :loading="submitting" @click="createDefaultColumn">新增列配置</el-button>
        </div>
        <el-table :data="sortedColumns" border stripe height="560" highlight-current-row @row-click="editColumn">
          <el-table-column prop="column_label" label="列名称" min-width="140" />
          <el-table-column prop="column_key" label="列标识" min-width="150" />
          <el-table-column prop="data_type" label="类型" width="120" />
          <el-table-column prop="sort_order" label="排序" width="80" />
          <el-table-column label="启用" width="70">
            <template #default="{ row }">{{ row.is_enabled ? "是" : "否" }}</template>
          </el-table-column>
          <el-table-column label="操作" width="80" fixed="right">
            <template #default="{ row }">
              <el-button link type="danger" @click.stop="handleDeleteColumn(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="column-editor">
        <div class="section-head">
          <div class="section-title">{{ editorTitle }}</div>
          <el-button text @click="resetForm">清空表单</el-button>
        </div>
        <el-form ref="formRef" :model="columnForm" :rules="rules" label-position="top" class="column-form">
          <div class="form-grid">
            <el-form-item label="列标识" prop="column_key">
              <el-input v-model="columnForm.column_key" placeholder="例如：review_time" />
            </el-form-item>

            <el-form-item label="列名称" prop="column_label">
              <el-input v-model="columnForm.column_label" placeholder="例如：回顾时间" />
            </el-form-item>

            <el-form-item label="字段类型" prop="data_type">
              <el-select v-model="columnForm.data_type" class="full-width">
                <el-option label="bool" value="bool" />
                <el-option label="string" value="string" />
                <el-option label="number" value="number" />
                <el-option label="datetime" value="datetime" />
                <el-option label="single_select" value="single_select" />
                <el-option label="multi_select" value="multi_select" />
                <el-option label="images" value="images" />
              </el-select>
            </el-form-item>

            <el-form-item label="列宽">
              <el-input-number v-model="columnForm.table_column_width" :min="60" :step="10" class="full-width" />
            </el-form-item>

            <el-form-item label="排序">
              <el-input-number v-model="columnForm.sort_order" :step="1" class="full-width" />
            </el-form-item>

            <el-form-item label="必填">
              <el-switch v-model="columnForm.is_required" />
            </el-form-item>

            <el-form-item label="启用">
              <el-switch v-model="columnForm.is_enabled" />
            </el-form-item>

            <el-form-item label="options_json" class="full-row">
              <el-input
                v-model="columnForm.options_json_text"
                type="textarea"
                :rows="10"
                :disabled="isImagesColumn"
                :placeholder="isImagesColumn ? 'images 类型固定为 []' : '例如：[{&quot;label&quot;:&quot;多&quot;,&quot;value&quot;:&quot;long&quot;}]'"
              />
            </el-form-item>
          </div>
        </el-form>
        <div class="editor-actions">
          <el-button type="primary" :loading="submitting" @click="submitForm">保存列配置</el-button>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped lang="less">
.column-config-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 16px;
}

.column-list,
.column-editor {
  min-width: 0;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.section-title {
  color: #1f2a3d;
  font-size: 16px;
  font-weight: 700;
}

.column-form {
  padding-right: 2px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 12px;
}

.full-row {
  grid-column: 1 / -1;
}

.full-width {
  width: 100%;
}

.editor-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

@media (max-width: 1000px) {
  .column-config-layout {
    grid-template-columns: 1fr;
  }
}
</style>
