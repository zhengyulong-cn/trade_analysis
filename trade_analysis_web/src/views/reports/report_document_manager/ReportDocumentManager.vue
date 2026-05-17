<script lang="ts" setup>
import {
  deleteReportDocumentApi,
  getReportDocumentItemApi,
  getReportDocumentListApi,
  uploadReportDocumentApi,
  type ReportDocument,
  type ReportDocumentListItem,
} from '@/api/modules'
import { Delete, Plus, RefreshRight, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules, type UploadFile, type UploadProps } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { formatDateTime } from '@/utils/date'

interface UploadFormState {
  published_at: string
  source: string
}

const loading = ref(false)
const uploading = ref(false)
const detailLoading = ref(false)
const deletingIds = ref<number[]>([])
const detailDialogVisible = ref(false)
const uploadDialogVisible = ref(false)
const documents = ref<ReportDocumentListItem[]>([])
const currentDocument = ref<ReportDocument | null>(null)
const uploadFormRef = ref<FormInstance>()
const uploadFileList = ref<UploadFile[]>([])
const selectedFile = ref<File | null>(null)
const uploadForm = reactive<UploadFormState>({
  published_at: '',
  source: '',
})

const uploadRules: FormRules<UploadFormState> = {
  published_at: [{ required: true, message: '请选择研报发布日期', trigger: 'change' }],
  source: [{ required: true, message: '请输入研报来源', trigger: 'blur' }],
}

const documentCountText = computed(() => `共 ${documents.value.length} 份研报`)

const loadDocuments = async () => {
  loading.value = true
  try {
    documents.value = await getReportDocumentListApi()
  } catch {
    ElMessage.error('获取研报列表失败')
  } finally {
    loading.value = false
  }
}

const formatFileSize = (size: number) => {
  if (size < 1024) {
    return `${size} B`
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`
  }
  return `${(size / (1024 * 1024)).toFixed(2)} MB`
}

const formatPublishedAt = (value: string | null) => value || '-'

const resetUploadForm = () => {
  uploadForm.published_at = ''
  uploadForm.source = ''
  uploadFileList.value = []
  selectedFile.value = null
  uploadFormRef.value?.clearValidate()
}

const openUploadDialog = () => {
  resetUploadForm()
  uploadDialogVisible.value = true
}

const closeUploadDialog = () => {
  uploadDialogVisible.value = false
  resetUploadForm()
}

const beforeUpload: UploadProps['beforeUpload'] = (file) => {
  const isPdf = file.type === 'application/pdf' || /\.pdf$/i.test(file.name)
  if (!isPdf) {
    ElMessage.error('当前只支持 PDF 文件')
    return false
  }
  return false
}

const handleUploadChange: UploadProps['onChange'] = (file, fileList) => {
  selectedFile.value = (file.raw as File | undefined) || null
  uploadFileList.value = fileList.slice(-1)
}

const handleUploadRemove: UploadProps['onRemove'] = () => {
  selectedFile.value = null
  uploadFileList.value = []
}

const submitUpload = async () => {
  const valid = await uploadFormRef.value?.validate().catch(() => false)
  if (!valid) {
    return
  }
  if (!selectedFile.value) {
    ElMessage.warning('请先选择研报 PDF 文件')
    return
  }

  uploading.value = true
  try {
    const result = await uploadReportDocumentApi({
      published_at: uploadForm.published_at,
      source: uploadForm.source.trim(),
      file: selectedFile.value,
    })
    documents.value = [result, ...documents.value]
    closeUploadDialog()
    ElMessage.success('研报上传并保存成功')
  } catch (error) {
    const response = error as { data?: { detail?: string } }
    ElMessage.error(response.data?.detail || '研报上传失败')
  } finally {
    uploading.value = false
  }
}

const handlePreviewText = async (row: ReportDocumentListItem) => {
  detailLoading.value = true
  detailDialogVisible.value = true
  currentDocument.value = null
  try {
    currentDocument.value = await getReportDocumentItemApi(row.report_id)
  } catch {
    detailDialogVisible.value = false
    ElMessage.error('获取研报正文失败')
  } finally {
    detailLoading.value = false
  }
}

const isDeleting = (reportId: number) => deletingIds.value.includes(reportId)

const handleDelete = async (row: ReportDocumentListItem) => {
  try {
    await ElMessageBox.confirm(
      `删除后将移除文件“${row.original_name}”及其提取文本，是否继续？`,
      '删除研报',
      { type: 'warning' },
    )
  } catch {
    return
  }

  deletingIds.value = [...deletingIds.value, row.report_id]
  try {
    await deleteReportDocumentApi(row.report_id)
    documents.value = documents.value.filter((item) => item.report_id !== row.report_id)
    if (currentDocument.value?.report_id === row.report_id) {
      detailDialogVisible.value = false
      currentDocument.value = null
    }
    ElMessage.success('研报删除成功')
  } catch {
    ElMessage.error('研报删除失败')
  } finally {
    deletingIds.value = deletingIds.value.filter((item) => item !== row.report_id)
  }
}

onMounted(() => {
  void loadDocuments()
})
</script>

<template>
  <div class="pageBox report-document-manager">
    <div class="toolbar">
      <div>
        <h2 class="title">研报管理</h2>
        <p class="subtitle">上传 PDF 研报，提取正文文本并持久化保存。</p>
      </div>
      <div class="toolbar-actions">
        <el-button type="primary" :icon="Plus" @click="openUploadDialog">上传研报</el-button>
        <el-button :loading="loading" :icon="RefreshRight" @click="loadDocuments">刷新</el-button>
      </div>
    </div>

    <div class="summary-bar">
      <span>{{ documentCountText }}</span>
    </div>

    <el-table
      v-loading="loading"
      :data="documents"
      border
      row-key="report_id"
      empty-text="暂无研报"
    >
      <el-table-column prop="report_id" label="ID" width="90" />
      <el-table-column prop="original_name" label="文件名" min-width="260" />
      <el-table-column prop="published_at" label="发布日期" width="130">
        <template #default="{ row }">
          {{ formatPublishedAt(row.published_at) }}
        </template>
      </el-table-column>
      <el-table-column prop="source" label="来源" min-width="180" />
      <el-table-column prop="content_type" label="类型" width="120" />
      <el-table-column label="大小" width="120">
        <template #default="{ row }">
          {{ formatFileSize(row.file_size) }}
        </template>
      </el-table-column>
      <el-table-column prop="parse_status" label="解析状态" width="120" />
      <el-table-column label="上传时间" min-width="180">
        <template #default="{ row }">
          {{ formatDateTime(row.create_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="handlePreviewText(row)">查看正文</el-button>
          <el-button
            type="danger"
            link
            :icon="Delete"
            :loading="isDeleting(row.report_id)"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="uploadDialogVisible" title="上传研报" width="34rem" @closed="resetUploadForm">
      <el-form ref="uploadFormRef" :model="uploadForm" :rules="uploadRules" label-width="7rem">
        <el-form-item label="发布日期" prop="published_at">
          <el-date-picker
            v-model="uploadForm.published_at"
            type="date"
            value-format="YYYY-MM-DD"
            format="YYYY-MM-DD"
            placeholder="请选择发布日期"
            class="full-width"
          />
        </el-form-item>
        <el-form-item label="研报来源" prop="source">
          <el-input v-model="uploadForm.source" placeholder="例如：中信期货、交易所官网" maxlength="255" />
        </el-form-item>
        <el-form-item label="上传研报">
          <el-upload
            :auto-upload="false"
            :show-file-list="true"
            :before-upload="beforeUpload"
            :on-change="handleUploadChange"
            :on-remove="handleUploadRemove"
            :file-list="uploadFileList"
            :limit="1"
            accept=".pdf,application/pdf"
          >
            <el-button :icon="UploadFilled">选择 PDF</el-button>
          </el-upload>
          <div class="upload-tip">当前仅支持 PDF，上传后会自动提取正文文本。</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeUploadDialog">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="submitUpload">确认上传</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailDialogVisible" title="研报正文" width="60rem">
      <div v-loading="detailLoading" class="document-detail">
        <template v-if="currentDocument">
          <div class="detail-meta">
            <div><strong>标题：</strong>{{ currentDocument.title || currentDocument.original_name }}</div>
            <div><strong>文件名：</strong>{{ currentDocument.original_name }}</div>
            <div><strong>发布日期：</strong>{{ formatPublishedAt(currentDocument.published_at) }}</div>
            <div><strong>来源：</strong>{{ currentDocument.source || '-' }}</div>
            <div><strong>类型：</strong>{{ currentDocument.content_type }}</div>
            <div><strong>上传时间：</strong>{{ formatDateTime(currentDocument.create_at) }}</div>
          </div>
          <el-scrollbar max-height="480px">
            <pre class="raw-text">{{ currentDocument.raw_text }}</pre>
          </el-scrollbar>
        </template>
      </div>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="less" scoped>
.report-document-manager {
  padding: 16px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.subtitle {
  margin: 6px 0 0;
  color: #909399;
  font-size: 13px;
}

.summary-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  color: #606266;
}

.document-detail {
  min-height: 120px;
}

.detail-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
  color: #303133;
}

.raw-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
  font-family: Consolas, 'Courier New', monospace;
  color: #303133;
}

.full-width {
  width: 100%;
}

.upload-tip {
  margin-top: 8px;
  color: #909399;
  font-size: 12px;
  line-height: 1.5;
}

@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .toolbar-actions {
    width: 100%;
    justify-content: flex-end;
    flex-wrap: wrap;
  }

  .detail-meta {
    grid-template-columns: 1fr;
  }
}
</style>
