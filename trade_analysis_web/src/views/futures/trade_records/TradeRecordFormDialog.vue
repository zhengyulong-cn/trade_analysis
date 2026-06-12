<script lang="ts" setup>
import {
  createTradeRecordApi,
  resolveTradeRecordImageUrl,
  updateTradeRecordApi,
  uploadTradeRecordImageApi,
  type TradeAccount,
  type TradeRecord,
  type TradeRecordColumn,
  type TradeRecordColumnOption,
  type TradeRecordImage,
  type TradeRecordImageUploadResult,
} from "@/api/modules"
import {
  ElMessage,
  type FormInstance,
  type FormRules,
  type UploadFile,
  type UploadProps,
  type UploadRawFile,
  type UploadRequestOptions,
} from "element-plus"
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue"

type DialogMode = "create" | "edit"
type TradeRecordFormValue = string | number | boolean | null | string[] | TradeRecordImage[]
type TradeRecordFormData = Record<string, TradeRecordFormValue>

const props = defineProps<{
  modelValue: boolean
  mode: DialogMode
  record: TradeRecord | null
  columns: TradeRecordColumn[]
  accounts: TradeAccount[]
}>()

const emit = defineEmits<{
  "update:modelValue": [value: boolean]
  saved: []
}>()

const MAX_IMAGE_COUNT = 12

const submitting = ref(false)
const formRef = ref<FormInstance>()
const formData = reactive<TradeRecordFormData>({})
const uploadFileMap = reactive<Record<string, UploadFile[]>>({})
const activeImageColumnKey = ref<string | null>(null)
let uploadUidSeed = 1

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit("update:modelValue", value),
})

const dialogTitle = computed(() => (props.mode === "create" ? "新增交易记录" : "编辑交易记录"))

const enabledColumns = computed(() =>
  [...props.columns]
    .filter((item) => item.is_enabled)
    .sort((a, b) => a.sort_order - b.sort_order || a.column_id - b.column_id),
)

const imageColumns = computed(() => enabledColumns.value.filter((item) => item.data_type === "images"))

const nextUploadUid = () => `trade-record-upload-${uploadUidSeed++}`

const toUploadError = (message: string): Error & { status?: number; method?: string; url?: string } => {
  const error = new Error(message) as Error & { status?: number; method?: string; url?: string }
  error.name = "UploadError"
  error.status = 500
  error.method = "POST"
  error.url = ""
  return error
}

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

const getNumberPrecision = (column: TradeRecordColumn) => {
  const option = Array.isArray(column.options_json) ? column.options_json[0] : undefined
  const precision = option && "precision" in option ? Number((option as Record<string, unknown>).precision) : NaN
  if (Number.isFinite(precision) && precision >= 0) {
    return precision
  }
  return 2
}

const getNumberStep = (column: TradeRecordColumn) => {
  const precision = getNumberPrecision(column)
  return precision <= 0 ? 1 : Number((1 / Math.pow(10, precision)).toFixed(precision))
}

const disableWeekendDate = (date: Date) => {
  const day = date.getDay()
  return day === 0 || day === 6
}

const disableHour = () => [2, 3, 4, 5, 6, 7, 8, 12, 16, 17, 18, 19, 20]

const normalizeImageItem = (item: TradeRecordImage): TradeRecordImage => ({
  path: item.path,
  original_name: item.original_name,
  content_type: item.content_type,
  size: item.size,
})

const toUploadFile = (image: TradeRecordImage): UploadFile => {
  const resolvedUrl = resolveTradeRecordImageUrl(image.path)
  return {
    uid: nextUploadUid(),
    name: image.original_name,
    url: resolvedUrl,
    status: "success",
    response: {
      ...image,
      url: resolvedUrl,
    },
  }
}

const resolveUploadPath = (uploadFile: UploadFile) => {
  const response = uploadFile.response as TradeRecordImageUploadResult | TradeRecordImage | undefined
  if (response?.path) {
    return response.path
  }
  if (!uploadFile.url) {
    return ""
  }
  return uploadFile.url.replace(/^.*\/storage\//, "")
}

const setActiveImageColumn = (columnKey: string) => {
  activeImageColumnKey.value = columnKey
}

const resolveTargetImageColumnKey = () => {
  if (
    activeImageColumnKey.value &&
    imageColumns.value.some((column) => column.column_key === activeImageColumnKey.value)
  ) {
    return activeImageColumnKey.value
  }

  if (imageColumns.value.length === 1) {
    return imageColumns.value[0].column_key
  }

  return imageColumns.value[0]?.column_key ?? null
}

const createEmptyFormData = () => {
  for (const key of Object.keys(formData)) {
    delete formData[key]
  }

  for (const key of Object.keys(uploadFileMap)) {
    uploadFileMap[key] = []
  }

  for (const column of enabledColumns.value) {
    if (column.data_type === "multi_select") {
      formData[column.column_key] = []
      continue
    }

    if (column.data_type === "images") {
      formData[column.column_key] = []
      uploadFileMap[column.column_key] = []
      continue
    }

    if (column.data_type === "bool") {
      formData[column.column_key] = false
      continue
    }

    formData[column.column_key] = null
  }

  activeImageColumnKey.value = imageColumns.value[0]?.column_key ?? null
}

const fillFormData = (record: TradeRecord) => {
  createEmptyFormData()

  for (const column of enabledColumns.value) {
    const value = record.data_json[column.column_key]

    if (column.data_type === "images") {
      const images = Array.isArray(value) ? (value as TradeRecordImage[]) : []
      formData[column.column_key] = images.map(normalizeImageItem)
      uploadFileMap[column.column_key] = images.map(toUploadFile)
      continue
    }

    if (column.data_type === "multi_select") {
      formData[column.column_key] = Array.isArray(value) ? [...value.map((item) => String(item))] : []
      continue
    }

    if (column.data_type === "bool") {
      formData[column.column_key] = Boolean(value)
      continue
    }

    formData[column.column_key] = (value as TradeRecordFormValue) ?? null
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
        trigger: column.data_type === "images" ? "change" : "blur",
      },
    ]
  }

  return rules
})

const beforeImageUpload = (rawFile: UploadRawFile) => {
  const isImage = ["image/jpeg", "image/png", "image/webp", "image/gif"].includes(rawFile.type)
  if (!isImage) {
    ElMessage.error("只支持 JPG、PNG、WEBP、GIF 图片")
    return false
  }
  return true
}

const appendUploadedImage = (columnKey: string, image: TradeRecordImage) => {
  const normalizedImage = normalizeImageItem(image)
  const current = Array.isArray(formData[columnKey]) ? [...(formData[columnKey] as TradeRecordImage[])] : []
  formData[columnKey] = [...current, normalizedImage]
  uploadFileMap[columnKey] = [...(uploadFileMap[columnKey] ?? []), toUploadFile(normalizedImage)]
}

const uploadImageForColumn = async (columnKey: string, file: File) => {
  const current = Array.isArray(formData[columnKey]) ? (formData[columnKey] as TradeRecordImage[]) : []
  if (current.length >= MAX_IMAGE_COUNT) {
    ElMessage.warning(`当前图片字段最多上传 ${MAX_IMAGE_COUNT} 张`)
    return
  }

  const result = await uploadTradeRecordImageApi(file)
  appendUploadedImage(columnKey, result)
}

const handleUploadRequest = (columnKey: string) => async (options: UploadRequestOptions) => {
  try {
    const result = await uploadTradeRecordImageApi(options.file)
    appendUploadedImage(columnKey, result)
    options.onSuccess?.(result)
  } catch {
    options.onError?.(toUploadError("截图上传失败"))
  }
}

const handleUploadRemove = (columnKey: string): UploadProps["onRemove"] => (uploadFile, uploadFiles) => {
  const removedPath = resolveUploadPath(uploadFile)
  const current = Array.isArray(formData[columnKey]) ? (formData[columnKey] as TradeRecordImage[]) : []
  formData[columnKey] = current.filter((item) => item.path !== removedPath)
  uploadFileMap[columnKey] = [...uploadFiles]
}

const handlePaste = async (event: ClipboardEvent) => {
  if (!dialogVisible.value || !imageColumns.value.length) {
    return
  }

  const clipboardItems = event.clipboardData?.items
  if (!clipboardItems?.length) {
    return
  }

  const imageItem = Array.from(clipboardItems).find((item) => item.type.startsWith("image/"))
  if (!imageItem) {
    return
  }

  const file = imageItem.getAsFile()
  const columnKey = resolveTargetImageColumnKey()
  if (!file || !columnKey) {
    ElMessage.warning("当前没有可粘贴图片的字段")
    return
  }

  event.preventDefault()

  try {
    await uploadImageForColumn(columnKey, file)
    ElMessage.success("图片已粘贴上传")
  } catch {
    ElMessage.error("截图上传失败")
  }
}

const buildPayload = () => {
  const dataJson: Record<string, unknown> = {}

  for (const column of enabledColumns.value) {
    const rawValue = formData[column.column_key]

    if (column.data_type === "images") {
      dataJson[column.column_key] = Array.isArray(rawValue) ? rawValue : []
      continue
    }

    if (column.data_type === "multi_select") {
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
      await createTradeRecordApi(payload)
      ElMessage.success("交易记录已创建")
    } else if (props.record) {
      await updateTradeRecordApi({
        trade_record_id: props.record.trade_record_id,
        ...payload,
      })
      ElMessage.success("交易记录已更新")
    }

    dialogVisible.value = false
    resetDialog()
    emit("saved")
  } catch {
    ElMessage.error(props.mode === "create" ? "创建交易记录失败" : "更新交易记录失败")
  } finally {
    submitting.value = false
  }
}

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      window.addEventListener("paste", handlePaste)
    } else {
      window.removeEventListener("paste", handlePaste)
    }

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

onBeforeUnmount(() => {
  window.removeEventListener("paste", handlePaste)
})
</script>

<template>
  <el-dialog v-model="dialogVisible" :title="dialogTitle" width="880px" destroy-on-close @closed="resetDialog">
    <el-form ref="formRef" :model="formData" :rules="buildRules" label-position="right" class="record-form">
      <div class="form-grid">
        <template v-for="column in enabledColumns" :key="column.column_id">
          <el-form-item
            v-if="column.data_type !== 'images'"
            label-width="100"
            :label="column.column_label"
            :prop="column.column_key"
            :class="{ 'full-row': column.data_type === 'multi_select' }"
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
              :disabled-date="disableWeekendDate"
              :disabled-hours="disableHour"
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
          </el-form-item>

          <el-form-item v-else :label="column.column_label" :prop="column.column_key" class="full-row">
            <div
              class="image-upload-field"
              :class="{ active: activeImageColumnKey === column.column_key }"
              @click="setActiveImageColumn(column.column_key)"
            >
              <el-upload
                :file-list="uploadFileMap[column.column_key] ?? []"
                list-type="picture-card"
                :auto-upload="true"
                :limit="MAX_IMAGE_COUNT"
                :before-upload="beforeImageUpload"
                :http-request="handleUploadRequest(column.column_key)"
                :on-remove="handleUploadRemove(column.column_key)"
                accept="image/jpeg,image/png,image/webp,image/gif"
              >
                <el-icon><Plus /></el-icon>
              </el-upload>
            </div>
            <div class="upload-tip">图片保存到 `storage/trade_records_v2`，最多 {{ MAX_IMAGE_COUNT }} 张，支持 `Ctrl+V` 粘贴截图</div>
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
.record-form {
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

.upload-tip {
  margin-top: 8px;
  color: #8c98aa;
  font-size: 12px;
}

.image-upload-field {
  display: inline-block;
  padding: 6px;
  border: 1px solid transparent;
  border-radius: 10px;
  transition: border-color 0.2s ease, background-color 0.2s ease;
}

.image-upload-field.active {
  border-color: #409eff;
  background: #f0f7ff;
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
