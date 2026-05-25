<script lang="ts" setup>
import {
  resolveTradeRecordScreenshotUrl,
  uploadTradeRecordScreenshotApi,
  type FutureContract,
  type TradeRecordCreateParams,
  type TradeRecordOpenDirection,
  type TradeRecordOpenSignal,
  type TradeRecordScreenshot,
  type TradeRecordScreenshotUploadResult,
  type TradeRecordSegmentType,
  type TradeRecordUpdateParams,
} from '@/api/modules'
import { Plus } from '@element-plus/icons-vue'
import {
  ElMessage,
  type FormInstance,
  type FormRules,
  type UploadFile,
  type UploadProps,
  type UploadRawFile,
  type UploadRequestOptions,
} from 'element-plus'
import { onBeforeUnmount, reactive, ref, watch } from 'vue'

interface TradeRecordFormModel {
  trade_record_id?: number
  contract: string
  open_direction: TradeRecordOpenDirection
  lots: number
  open_time: string
  open_price: number
  close_time: string
  close_price: number | null
  segment_type: TradeRecordSegmentType
  open_signal: TradeRecordOpenSignal | null
  fee: number
  actual_pnl: number | null
  screenshots: TradeRecordScreenshot[]
  comment: string
}

const props = defineProps<{
  visible: boolean
  mode: 'create' | 'edit'
  submitting: boolean
  contracts: FutureContract[]
  openSignalOptions: Array<{ label: string; value: TradeRecordOpenSignal }>
  initialValue: TradeRecordFormModel
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'submit', payload: TradeRecordCreateParams | TradeRecordUpdateParams): void
}>()

const segmentTypeOptions: Array<{ label: string; value: TradeRecordSegmentType }> = [
  { label: '趋势推动段', value: 'trend_push' },
  { label: '趋势回调段', value: 'trend_pullback' },
  { label: '区间内部段', value: 'range_internal' },
  { label: '（假突破）回调转区间段', value: 'false_break_range_transition' },
  { label: '（真突破）区间转推动段', value: 'true_break_trend_push_transition' },
]

const openDirectionOptions: Array<{ label: string; value: TradeRecordOpenDirection }> = [
  { label: '多单', value: 'long' },
  { label: '空单', value: 'short' },
]

const formRef = ref<FormInstance>()
const uploadFileList = ref<UploadFile[]>([])
let uploadUidSeed = 1

const form = reactive<TradeRecordFormModel>({
  contract: '',
  open_direction: 'long',
  lots: 1,
  open_time: '',
  open_price: 0,
  close_time: '',
  close_price: null,
  segment_type: 'trend_push',
  open_signal: null,
  fee: 0,
  actual_pnl: null,
  screenshots: [],
  comment: '',
})

const rules = reactive<FormRules<TradeRecordFormModel>>({
  contract: [{ required: true, message: '请选择合约', trigger: 'change' }],
  open_direction: [{ required: true, message: '请选择开仓方向', trigger: 'change' }],
  lots: [{ required: true, message: '请输入手数', trigger: 'change' }],
  open_time: [{ required: true, message: '请选择开仓时间', trigger: 'change' }],
  open_price: [{ required: true, message: '请输入开仓价格', trigger: 'change' }],
  segment_type: [{ required: true, message: '请选择30F线段类型', trigger: 'change' }],
  fee: [{ required: true, message: '请输入手续费', trigger: 'change' }],
})

const nextUploadUid = () => uploadUidSeed++

const dialogTitle = () => (props.mode === 'create' ? '新增交易记录' : '修改交易记录')

const disableFutureDateTime = (date: Date) => date.getTime() > Date.now()

const syncFromProps = () => {
  form.trade_record_id = props.initialValue.trade_record_id
  form.contract = props.initialValue.contract
  form.open_direction = props.initialValue.open_direction
  form.lots = props.initialValue.lots
  form.open_time = props.initialValue.open_time
  form.open_price = props.initialValue.open_price
  form.close_time = props.initialValue.close_time
  form.close_price = props.initialValue.close_price
  form.segment_type = props.initialValue.segment_type
  form.open_signal = props.initialValue.open_signal
  form.fee = props.initialValue.fee
  form.actual_pnl = props.initialValue.actual_pnl
  form.screenshots = [...props.initialValue.screenshots]
  form.comment = props.initialValue.comment
  uploadFileList.value = props.initialValue.screenshots.map((item) => {
    const url = resolveTradeRecordScreenshotUrl(item.path)
    return {
      uid: nextUploadUid(),
      name: item.original_name,
      url,
      status: 'success',
      response: {
        ...item,
        url,
      },
    }
  })
  formRef.value?.clearValidate()
}

const validateScreenshotFile = (rawFile: Pick<UploadRawFile, 'type' | 'size'>) => {
  const isImage = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'].includes(rawFile.type)
  if (!isImage) {
    ElMessage.error('仅支持 JPG、PNG、WEBP、GIF 图片')
    return false
  }

  const isLt10Mb = rawFile.size / 1024 / 1024 < 10
  if (!isLt10Mb) {
    ElMessage.error('图片大小不能超过 10MB')
    return false
  }

  return true
}

const toUploadError = (message: string, options: UploadRequestOptions): Parameters<NonNullable<typeof options.onError>>[0] => ({
  name: 'UploadError',
  message,
  status: 500,
  method: 'POST',
  url: '',
})

const applyUploadedScreenshot = (result: TradeRecordScreenshotUploadResult) => {
  form.screenshots = [
    ...form.screenshots,
    {
      path: result.path,
      original_name: result.original_name,
      content_type: result.content_type,
      size: result.size,
    },
  ]
  uploadFileList.value = [
    ...uploadFileList.value,
    {
      uid: nextUploadUid(),
      name: result.original_name,
      url: result.url,
      status: 'success',
      response: result,
    },
  ]
}

const handleUploadRequest = async (options: UploadRequestOptions) => {
  try {
    const result = await uploadTradeRecordScreenshotApi(options.file)
    applyUploadedScreenshot(result)
    options.onSuccess?.(result)
    ElMessage.success('截图上传成功')
  } catch (error) {
    options.onError?.(toUploadError(error instanceof Error ? error.message : '截图上传失败', options))
    ElMessage.error('截图上传失败')
  }
}

const resolveUploadPath = (uploadFile: UploadFile) => {
  const response = uploadFile.response as TradeRecordScreenshotUploadResult | TradeRecordScreenshot | undefined
  if (response?.path) {
    return response.path
  }
  if (!uploadFile.url) {
    return ''
  }
  return uploadFile.url.replace(/^.*\/storage\//, '')
}

const handleUploadRemove: UploadProps['onRemove'] = (uploadFile, uploadFiles) => {
  const removedPath = resolveUploadPath(uploadFile)
  form.screenshots = form.screenshots.filter((item) => item.path !== removedPath)
  uploadFileList.value = uploadFiles
}

const handlePasteScreenshot = async (event: ClipboardEvent) => {
  if (!props.visible) {
    return
  }

  const items = Array.from(event.clipboardData?.items ?? [])
  const imageFiles = items
    .filter((item) => item.kind === 'file' && item.type.startsWith('image/'))
    .map((item) => item.getAsFile())
    .filter((file): file is File => file !== null)

  if (!imageFiles.length) {
    return
  }

  event.preventDefault()

  for (const file of imageFiles) {
    if (!validateScreenshotFile(file)) {
      continue
    }

    try {
      const result = await uploadTradeRecordScreenshotApi(file)
      applyUploadedScreenshot(result)
      ElMessage.success('截图粘贴上传成功')
    } catch {
      ElMessage.error('截图粘贴上传失败')
    }
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

  const hasCloseTime = Boolean(form.close_time)
  const hasClosePrice = form.close_price !== null
  if (hasCloseTime !== hasClosePrice) {
    ElMessage.error('平仓时间和平仓价格需要同时填写，或同时留空')
    return
  }
  if (hasCloseTime && new Date(form.close_time).getTime() < new Date(form.open_time).getTime()) {
    ElMessage.error('平仓时间不能早于开仓时间')
    return
  }

  const basePayload: TradeRecordCreateParams = {
    contract: form.contract.trim(),
    open_direction: form.open_direction,
    lots: form.lots,
    open_time: form.open_time,
    open_price: form.open_price,
    close_time: hasCloseTime ? form.close_time : null,
    close_price: hasClosePrice ? form.close_price : null,
    segment_type: form.segment_type,
    open_signal: form.open_signal,
    fee: form.fee,
    actual_pnl: form.actual_pnl,
    screenshots: [...form.screenshots],
    comment: form.comment.trim() || null,
  }

  if (props.mode === 'create') {
    emit('submit', basePayload)
    return
  }

  emit('submit', {
    trade_record_id: form.trade_record_id!,
    ...basePayload,
  })
}

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      syncFromProps()
      window.addEventListener('paste', handlePasteScreenshot)
      return
    }
    window.removeEventListener('paste', handlePasteScreenshot)
  },
)

onBeforeUnmount(() => {
  window.removeEventListener('paste', handlePasteScreenshot)
})
</script>

<template>
  <el-dialog
    :model-value="visible"
    :title="dialogTitle()"
    width="48rem"
    @update:model-value="emit('update:visible', $event)"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="8rem" class="trade-form">
      <div class="form-grid">
        <el-form-item label="合约" prop="contract">
          <el-select v-model="form.contract" filterable placeholder="请选择合约" style="width: 100%">
            <el-option
              v-for="contractItem in contracts"
              :key="contractItem.contract_id"
              :label="contractItem.symbol"
              :value="contractItem.symbol"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="开仓方向" prop="open_direction">
          <el-select v-model="form.open_direction" placeholder="请选择开仓方向" style="width: 100%">
            <el-option
              v-for="option in openDirectionOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="手数" prop="lots">
          <el-input-number v-model="form.lots" :min="1" :step="1" :precision="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="开仓时间" prop="open_time">
          <el-date-picker
            v-model="form.open_time"
            type="datetime"
            placeholder="请选择开仓时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            :disabled-date="disableFutureDateTime"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="开仓价格" prop="open_price">
          <el-input-number v-model="form.open_price" :min="0" :precision="1" :step="0.5" style="width: 100%" />
        </el-form-item>
        <el-form-item label="平仓时间">
          <el-date-picker
            v-model="form.close_time"
            type="datetime"
            placeholder="未平仓可留空"
            value-format="YYYY-MM-DD HH:mm:ss"
            :disabled-date="disableFutureDateTime"
            clearable
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="平仓价格">
          <el-input-number
            v-model="form.close_price"
            :min="0"
            :precision="1"
            :step="0.5"
            controls-position="right"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="30F线段类型" prop="segment_type">
          <el-select v-model="form.segment_type" placeholder="请选择30F线段类型" style="width: 100%">
            <el-option
              v-for="option in segmentTypeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="开仓信号">
          <el-select v-model="form.open_signal" clearable placeholder="可留空" style="width: 100%">
            <el-option
              v-for="option in openSignalOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="手续费" prop="fee">
          <el-input-number v-model="form.fee" :min="0" :precision="2" :step="0.01" style="width: 100%" />
        </el-form-item>
        <el-form-item label="实际盈亏">
          <el-input-number v-model="form.actual_pnl" :precision="2" :step="1" style="width: 100%" />
        </el-form-item>
      </div>

      <el-form-item label="操作截图">
        <el-upload
          :file-list="uploadFileList"
          list-type="picture-card"
          accept=".jpg,.jpeg,.png,.webp,.gif"
          :auto-upload="true"
          :before-upload="validateScreenshotFile"
          :http-request="handleUploadRequest"
          :on-remove="handleUploadRemove"
          multiple
        >
          <el-icon><Plus /></el-icon>
        </el-upload>
        <div class="upload-tip">支持点击上传，也支持在弹窗打开时按 Ctrl+V 粘贴截图</div>
      </el-form-item>

      <el-form-item label="操作评价">
        <el-input
          v-model="form.comment"
          type="textarea"
          :rows="4"
          maxlength="2000"
          show-word-limit
          placeholder="请输入操作评价"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submitForm">确认</el-button>
    </template>
  </el-dialog>
</template>

<style lang="less" scoped>
.trade-form {
  padding-right: 12px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.upload-tip {
  font-size: 12px;
  line-height: 1.5;
  color: #909399;
}

@media (max-width: 960px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
