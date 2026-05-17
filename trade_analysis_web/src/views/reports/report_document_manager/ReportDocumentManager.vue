<script lang="ts" setup>
import {
  deleteReportDocumentApi,
  getReportDocumentItemApi,
  getReportDocumentListApi,
  uploadReportDocumentApi,
  type ReportDocument,
  type ReportDocumentListItem,
} from '@/api/modules'
import { Delete, Document, RefreshRight, UploadFilled } from '@element-plus/icons-vue'
import {
  ElMessage,
  ElMessageBox,
  type UploadFile,
  type UploadProps,
  type UploadRequestOptions,
} from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { formatDateTime } from '@/utils/date'

const loading = ref(false)
const uploading = ref(false)
const detailLoading = ref(false)
const deletingIds = ref<number[]>([])
const dialogVisible = ref(false)
const documents = ref<ReportDocumentListItem[]>([])
const currentDocument = ref<ReportDocument | null>(null)
const uploadFileList = ref<UploadFile[]>([])

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

const handleUploadReport = async (options: UploadRequestOptions) => {
  uploading.value = true
  try {
    const result = await uploadReportDocumentApi(options.file as File)
    documents.value = [result, ...documents.value]
    uploadFileList.value = []
    ElMessage.success('研报上传并解析成功')
  } catch (error) {
    const response = error as { data?: { detail?: string } }
    ElMessage.error(response.data?.detail || '研报上传失败')
  } finally {
    uploading.value = false
  }
}

const beforeUpload: UploadProps['beforeUpload'] = (file) => {
  const isSupported = file.type === 'application/pdf' || file.type === 'text/plain' || /\.txt$/i.test(file.name)
  if (!isSupported) {
    ElMessage.error('当前只支持 pdf 和 txt 文件')
    return false
  }
  return true
}

const handlePreviewText = async (row: ReportDocumentListItem) => {
  detailLoading.value = true
  dialogVisible.value = true
  currentDocument.value = null
  try {
    currentDocument.value = await getReportDocumentItemApi(row.report_id)
  } catch {
    dialogVisible.value = false
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
      dialogVisible.value = false
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
        <p class="subtitle">上传研报文件，抽取正文文本并保存，当前支持 PDF 与 TXT。</p>
      </div>
      <div class="toolbar-actions">
        <el-upload
          :show-file-list="false"
          :http-request="handleUploadReport"
          :before-upload="beforeUpload"
          :file-list="uploadFileList"
          accept=".pdf,.txt,text/plain,application/pdf"
        >
          <el-button type="primary" :loading="uploading" :icon="UploadFilled">上传研报</el-button>
        </el-upload>
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
      <el-table-column prop="content_type" label="类型" min-width="150" />
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

    <el-dialog v-model="dialogVisible" title="研报正文" width="60rem">
      <div v-loading="detailLoading" class="document-detail">
        <template v-if="currentDocument">
          <div class="detail-meta">
            <div><strong>标题：</strong>{{ currentDocument.title || currentDocument.original_name }}</div>
            <div><strong>文件名：</strong>{{ currentDocument.original_name }}</div>
            <div><strong>类型：</strong>{{ currentDocument.content_type }}</div>
            <div><strong>上传时间：</strong>{{ formatDateTime(currentDocument.create_at) }}</div>
          </div>
          <el-scrollbar max-height="480px">
            <pre class="raw-text">{{ currentDocument.raw_text }}</pre>
          </el-scrollbar>
        </template>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
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
