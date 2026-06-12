<script lang="ts" setup>
import {
  createOpportunityReviewApi,
  updateOpportunityReviewApi,
  type OpportunityReview,
  type OpportunityReviewColumn,
  type OpportunityReviewColumnOption,
} from "@/api/modules"
import { ElMessage, type FormInstance, type FormRules } from "element-plus"
import { computed, reactive, ref, watch } from "vue"

type DialogMode = "create" | "edit"
type FormValue = string | number | boolean | null | string[] | unknown[]
type FormData = Record<string, FormValue>

const props = defineProps<{
  modelValue: boolean
  mode: DialogMode
  record: OpportunityReview | null
  columns: OpportunityReviewColumn[]
}>()

const emit = defineEmits<{
  "update:modelValue": [value: boolean]
  saved: []
}>()

const submitting = ref(false)
const formRef = ref<FormInstance>()
const formData = reactive<FormData>({})

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit("update:modelValue", value),
})

const dialogTitle = computed(() => (props.mode === "create" ? "新增机会回顾记录" : "编辑机会回顾记录"))

const enabledColumns = computed(() =>
  [...props.columns]
    .filter((item) => item.is_enabled)
    .sort((a, b) => a.sort_order - b.sort_order || a.column_id - b.column_id),
)

const getColumnOptions = (column: OpportunityReviewColumn): OpportunityReviewColumnOption[] =>
  (column.options_json ?? []) as OpportunityReviewColumnOption[]

const getNumberPrecision = (column: OpportunityReviewColumn) => {
  const option = Array.isArray(column.options_json) ? column.options_json[0] : undefined
  const precision = option && "precision" in option ? Number((option as Record<string, unknown>).precision) : NaN
  if (Number.isFinite(precision) && precision >= 0) {
    return precision
  }
  return 2
}

const getNumberStep = (column: OpportunityReviewColumn) => {
  const precision = getNumberPrecision(column)
  return precision <= 0 ? 1 : Number((1 / Math.pow(10, precision)).toFixed(precision))
}

const createEmptyFormData = () => {
  for (const key of Object.keys(formData)) {
    delete formData[key]
  }

  for (const column of enabledColumns.value) {
    if (column.data_type === "multi_select" || column.data_type === "images") {
      formData[column.column_key] = []
      continue
    }

    if (column.data_type === "bool") {
      formData[column.column_key] = false
      continue
    }

    formData[column.column_key] = null
  }
}

const fillFormData = (record: OpportunityReview) => {
  createEmptyFormData()

  for (const column of enabledColumns.value) {
    const value = record.data_json[column.column_key]

    if (column.data_type === "multi_select" || column.data_type === "images") {
      formData[column.column_key] = Array.isArray(value) ? [...value.map((item) => String(item))] : []
      continue
    }

    if (column.data_type === "bool") {
      formData[column.column_key] = Boolean(value)
      continue
    }

    formData[column.column_key] = (value as FormValue) ?? null
  }
}

const buildRules = computed<FormRules>(() => {
  const rules: FormRules = {}

  for (const column of enabledColumns.value) {
    if (!column.is_required) {
      continue
    }

    rules[column.column_key] = [
      {
        required: true,
        validator: (_rule, value, callback) => {
          if (value === null || value === undefined) {
            callback(new Error(`请填写${column.column_label}`))
            return
          }
          if (typeof value === "string" && !value.trim()) {
            callback(new Error(`请填写${column.column_label}`))
            return
          }
          if (Array.isArray(value) && value.length === 0) {
            callback(new Error(`请填写${column.column_label}`))
            return
          }
          callback()
        },
        trigger: column.data_type === "multi_select" ? "change" : "blur",
      },
    ]
  }

  return rules
})

const buildPayload = () => {
  const dataJson: Record<string, unknown> = {}

  for (const column of enabledColumns.value) {
    const rawValue = formData[column.column_key]

    if (column.data_type === "multi_select" || column.data_type === "images") {
      dataJson[column.column_key] = Array.isArray(rawValue) ? rawValue : []
      continue
    }

    if (column.data_type === "bool") {
      dataJson[column.column_key] = Boolean(rawValue)
      continue
    }

    if (rawValue === null || rawValue === undefined) {
      dataJson[column.column_key] = null
      continue
    }

    if (typeof rawValue === "string") {
      dataJson[column.column_key] = rawValue.trim() || null
      continue
    }

    dataJson[column.column_key] = rawValue
  }

  return { data_json: dataJson }
}

const resetDialog = () => {
  createEmptyFormData()
  formRef.value?.clearValidate()
}

const submitForm = async () => {
  if (!formRef.value) {
    return
  }

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }

  submitting.value = true
  try {
    const payload = buildPayload()
    if (props.mode === "create") {
      await createOpportunityReviewApi(payload)
      ElMessage.success("机会回顾记录已创建")
    } else if (props.record) {
      await updateOpportunityReviewApi({
        opportunity_review_id: props.record.opportunity_review_id,
        ...payload,
      })
      ElMessage.success("机会回顾记录已更新")
    }

    dialogVisible.value = false
    resetDialog()
    emit("saved")
  } catch {
    ElMessage.error(props.mode === "create" ? "创建机会回顾记录失败" : "更新机会回顾记录失败")
  } finally {
    submitting.value = false
  }
}

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) {
      return
    }

    if (props.mode === "edit" && props.record) {
      fillFormData(props.record)
      return
    }

    createEmptyFormData()
  },
)
</script>

<template>
  <el-dialog v-model="dialogVisible" :title="dialogTitle" width="880px" destroy-on-close @closed="resetDialog">
    <el-form ref="formRef" :model="formData" :rules="buildRules" label-position="right" class="review-form">
      <div class="form-grid">
        <template v-for="column in enabledColumns" :key="column.column_id">
          <el-form-item
            label-width="110"
            :label="column.column_label"
            :prop="column.column_key"
            :class="{ 'full-row': column.data_type === 'multi_select' || column.data_type === 'images' }"
          >
            <el-switch v-if="column.data_type === 'bool'" v-model="formData[column.column_key]" />

            <el-input
              v-else-if="column.data_type === 'string'"
              v-model="formData[column.column_key]"
              clearable
              :placeholder="`请输入${column.column_label}`"
            />

            <el-input-number
              v-else-if="column.data_type === 'number'"
              v-model="formData[column.column_key]"
              :precision="getNumberPrecision(column)"
              :step="getNumberStep(column)"
              controls-position="right"
              class="full-width"
            />

            <el-date-picker
              v-else-if="column.data_type === 'datetime'"
              v-model="formData[column.column_key]"
              type="datetime"
              value-format="YYYY-MM-DD HH:mm:ss"
              class="full-width"
              :placeholder="`请选择${column.column_label}`"
            />

            <el-select
              v-else-if="column.data_type === 'single_select'"
              v-model="formData[column.column_key]"
              clearable
              filterable
              class="full-width"
              :placeholder="`请选择${column.column_label}`"
            >
              <el-option
                v-for="option in getColumnOptions(column)"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>

            <el-select
              v-else-if="column.data_type === 'multi_select'"
              v-model="formData[column.column_key]"
              multiple
              clearable
              filterable
              class="full-width"
              :placeholder="`请选择${column.column_label}`"
            >
              <el-option
                v-for="option in getColumnOptions(column)"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>

            <el-alert v-else-if="column.data_type === 'images'" type="info" :closable="false" title="图片字段稍后接入上传" />
          </el-form-item>
        </template>
      </div>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">
          {{ mode === "create" ? "创建" : "保存" }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped lang="less">
.review-form {
  padding-top: 4px;
}

.form-grid {
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

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 900px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .full-row {
    grid-column: auto;
  }
}
</style>
