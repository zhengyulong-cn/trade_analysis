<script lang="ts" setup>
import {
  createTradeRecordApi,
  deleteTradeRecordApi,
  getTradeAccountListApi,
  getTradeRecordColumnListApi,
  getTradeRecordListApi,
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
import { formatDateTime } from "@/utils/date"
import TradeRecordColumnConfigDialog from "./TradeRecordColumnConfigDialog.vue"
import {
  ElMessage,
  ElMessageBox,
  type FormInstance,
  type FormRules,
  type UploadFile,
  type UploadProps,
  type UploadRawFile,
  type UploadRequestOptions,
} from "element-plus"
import { computed, onMounted, reactive, ref } from "vue"

type TradeRecordFormValue = string | number | boolean | null | string[] | TradeRecordImage[]
type TradeRecordFormData = Record<string, TradeRecordFormValue>

const MAX_IMAGE_COUNT = 12
const DEFAULT_TABLE_MIN_WIDTH = 160

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const columnDialogVisible = ref(false)
const dialogMode = ref<"create" | "edit">("create")
const columns = ref<TradeRecordColumn[]>([])
const accounts = ref<TradeAccount[]>([])
const records = ref<TradeRecord[]>([])
const formRef = ref<FormInstance>()
const formData = reactive<TradeRecordFormData>({})
const uploadFileMap = reactive<Record<string, UploadFile[]>>({})
const editingRecordId = ref<number | null>(null)
let uploadUidSeed = 1

const enabledColumns = computed(() =>
  [...columns.value]
    .filter((item) => item.is_enabled)
    .sort((a, b) => a.sort_order - b.sort_order || a.column_id - b.column_id),
)

const dialogTitle = computed(() => (dialogMode.value === "create" ? "新增交易记录" : "编辑交易记录"))

const nextUploadUid = () => `trade-record-upload-${uploadUidSeed++}`

const toUploadError = (message: string): Error & { status?: number; method?: string; url?: string } => {
  const error = new Error(message) as Error & { status?: number; method?: string; url?: string }
  error.name = "UploadError"
  error.status = 500
  error.method = "POST"
  error.url = ""
  return error
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

const getNumberStep = (column: TradeRecordColumn) => {
  const precision = getNumberPrecision(column)
  return precision <= 0 ? 1 : Number((1 / Math.pow(10, precision)).toFixed(precision))
}

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

const beforeImageUpload = (rawFile: UploadRawFile) => {
  const isImage = ["image/jpeg", "image/png", "image/webp", "image/gif"].includes(rawFile.type)
  if (!isImage) {
    ElMessage.error("只支持 JPG、PNG、WEBP、GIF 图片")
    return false
  }
  return true
}

const handleUploadRequest = (columnKey: string) => async (options: UploadRequestOptions) => {
  try {
    const result = await uploadTradeRecordImageApi(options.file)
    const current = Array.isArray(formData[columnKey]) ? [...(formData[columnKey] as TradeRecordImage[])] : []
    formData[columnKey] = [...current, normalizeImageItem(result)]
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

const formatCellValue = (column: TradeRecordColumn, value: unknown) => {
  if (value === null || value === undefined || value === "") {
    return "-"
  }

  if (column.data_type === "datetime") {
    return formatDateTime(String(value))
  }

  if (column.data_type === "bool") {
    return value ? "是" : "否"
  }

  if (column.data_type === "single_select") {
    const matched = getColumnOptions(column).find((item) => item.value === String(value))
    return matched?.label ?? String(value)
  }

  if (column.data_type === "multi_select") {
    const values = Array.isArray(value) ? value : []
    const optionMap = new Map(getColumnOptions(column).map((item) => [item.value, item.label]))
    return values.map((item) => optionMap.get(String(item)) ?? String(item)).join("、") || "-"
  }

  if (column.data_type === "images") {
    return Array.isArray(value) ? `${value.length} 张` : "-"
  }

  return String(value)
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
  editingRecordId.value = null
  createEmptyFormData()
  formRef.value?.clearValidate()
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
    if (!dialogVisible.value) {
      createEmptyFormData()
    }
  } catch {
    ElMessage.error("交易记录页面数据加载失败")
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  dialogMode.value = "create"
  resetDialog()
  dialogVisible.value = true
}

const openEditDialog = (record: TradeRecord) => {
  dialogMode.value = "edit"
  resetDialog()
  editingRecordId.value = record.trade_record_id

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

  dialogVisible.value = true
}

const openColumnDialog = () => {
  columnDialogVisible.value = true
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
    if (dialogMode.value === "create") {
      await createTradeRecordApi(payload)
      ElMessage.success("交易记录已创建")
    } else if (editingRecordId.value !== null) {
      await updateTradeRecordApi({
        trade_record_id: editingRecordId.value,
        ...payload,
      })
      ElMessage.success("交易记录已更新")
    }

    dialogVisible.value = false
    resetDialog()
    await loadPageData()
  } catch {
    ElMessage.error(dialogMode.value === "create" ? "创建交易记录失败" : "更新交易记录失败")
  } finally {
    submitting.value = false
  }
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
    <el-card shadow="never" class="manager-card">
      <template #header>
        <div class="toolbar">
          <div class="toolbar-left">
            <div class="toolbar-title">交易记录</div>
            <div class="toolbar-subtitle">每条交易记录对应一行，字段由 `trade_record_columns` 动态驱动</div>
          </div>

          <div class="toolbar-right">
            <div class="summary">{{ records.length }} 条记录</div>
            <el-button @click="loadPageData">刷新</el-button>
            <el-button type="primary" @click="openCreateDialog">新增交易记录</el-button>
            <el-button type="warning" @click="openColumnDialog">列配置</el-button>
          </div>
        </div>
      </template>

      <el-empty v-if="!loading && !records.length" description="暂无交易记录" />

      <el-table v-else v-loading="loading" :data="records" border stripe class="record-table">
        <el-table-column prop="trade_record_id" label="ID" width="90" fixed="left" />
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
        <el-table-column label="创建时间" min-width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="880px" destroy-on-close @closed="resetDialog">
      <el-form ref="formRef" :model="formData" :rules="buildRules" label-position="right" class="record-form">
        <div class="form-grid">
          <template v-for="column in enabledColumns" :key="column.column_id">
            <el-form-item
              v-if="column.data_type !== 'images'"
              label-width="80"
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
              <el-upload
                v-model:file-list="uploadFileMap[column.column_key]"
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
              <div class="upload-tip">图片保存到 `storage/trade_records_v2`，最多 {{ MAX_IMAGE_COUNT }} 张</div>
            </el-form-item>
          </template>
        </div>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="submitForm">
            {{ dialogMode === "create" ? "创建" : "保存" }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <TradeRecordColumnConfigDialog v-model="columnDialogVisible" :columns="columns" @changed="loadPageData" />
  </section>
</template>

<style scoped lang="less">
.trade-record-page {
  padding: 16px;
}

.manager-card {
  border: none;
  border-radius: 18px;
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

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 900px) {
  .toolbar {
    flex-direction: column;
  }

  .toolbar-right {
    width: 100%;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .full-row {
    grid-column: auto;
  }
}
</style>
