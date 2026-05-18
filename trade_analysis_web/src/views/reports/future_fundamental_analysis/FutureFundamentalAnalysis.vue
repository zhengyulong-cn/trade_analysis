<script lang="ts" setup>
import {
  createFutureFundamentalAnalysisApi,
  deleteFutureFundamentalAnalysisApi,
  deleteFutureReportDocumentApi,
  getFutureFundamentalAnalysisListApi,
  getFutureProductList,
  getFutureReportDocumentListApi,
  resolveFutureReportPdfUrl,
  updateFutureFundamentalAnalysisApi,
  uploadFutureReportDocumentApi,
  type FutureFundamentalAnalysis,
  type FutureProduct,
  type FutureReportDocument,
} from "@/api/modules"
import { formatDateTime as formatDateTimeByDayjs } from "@/utils/date"
import { ElMessage, ElMessageBox, type FormInstance, type FormRules, type UploadFile } from "element-plus"
import { computed, onMounted, reactive, ref } from "vue"

interface AnalysisForm {
  analysis_id?: number
  product_id: number | null
  report_id: number | null
  supply_side: string
  demand_side: string
  inventory_side: string
  industry_profit: string
  substitution_linkage: string
  policy_macro: string
  conclusion: string
}

interface ReportUploadForm {
  published_at: string
  report_source: string
  file: File | null
}

const reports = ref<FutureReportDocument[]>([])
const analyses = ref<FutureFundamentalAnalysis[]>([])
const products = ref<FutureProduct[]>([])

const reportLoading = ref(false)
const reportSubmitting = ref(false)
const analysisLoading = ref(false)
const submitting = ref(false)

const dialogVisible = ref(false)
const dialogMode = ref<"create" | "edit">("create")
const formRef = ref<FormInstance>()

const reportUploadDialogVisible = ref(false)
const reportUploadFormRef = ref<FormInstance>()

const form = reactive<AnalysisForm>({
  product_id: null,
  report_id: null,
  supply_side: "",
  demand_side: "",
  inventory_side: "",
  industry_profit: "",
  substitution_linkage: "",
  policy_macro: "",
  conclusion: "",
})

const reportUploadForm = reactive<ReportUploadForm>({
  published_at: "",
  report_source: "",
  file: null,
})

const rules = reactive<FormRules<AnalysisForm>>({
  product_id: [{ required: true, message: "请选择产品", trigger: "change" }],
  report_id: [{ required: true, message: "请选择研报", trigger: "change" }],
})

const reportUploadRules = reactive<FormRules<ReportUploadForm>>({
  published_at: [{ required: true, message: "请选择发布时间", trigger: "change" }],
  report_source: [{ required: true, message: "请输入来源", trigger: "blur" }],
  file: [{ required: true, message: "请上传PDF文件", trigger: "change" }],
})

const dialogTitle = computed(() => (dialogMode.value === "create" ? "新增基本面分析" : "编辑基本面分析"))

const sortProducts = (items: FutureProduct[]) => {
  return [...items].sort((first, second) => first.product_code.localeCompare(second.product_code, "zh-CN"))
}

const sortReports = (items: FutureReportDocument[]) => {
  return [...items].sort((first, second) => second.published_at.localeCompare(first.published_at))
}

const loadProducts = async () => {
  try {
    products.value = sortProducts(await getFutureProductList())
  } catch {
    ElMessage.error("获取产品列表失败")
  }
}

const loadReports = async () => {
  reportLoading.value = true
  try {
    reports.value = sortReports(await getFutureReportDocumentListApi())
  } catch {
    ElMessage.error("获取研报列表失败")
  } finally {
    reportLoading.value = false
  }
}

const loadAnalyses = async () => {
  analysisLoading.value = true
  try {
    analyses.value = await getFutureFundamentalAnalysisListApi()
  } catch {
    ElMessage.error("获取基本面分析失败")
  } finally {
    analysisLoading.value = false
  }
}

const resetForm = () => {
  form.analysis_id = undefined
  form.product_id = null
  form.report_id = null
  form.supply_side = ""
  form.demand_side = ""
  form.inventory_side = ""
  form.industry_profit = ""
  form.substitution_linkage = ""
  form.policy_macro = ""
  form.conclusion = ""
  formRef.value?.clearValidate()
}

const resetReportUploadForm = () => {
  reportUploadForm.published_at = ""
  reportUploadForm.report_source = ""
  reportUploadForm.file = null
  reportUploadFormRef.value?.clearValidate()
}

const openCreateDialog = () => {
  dialogMode.value = "create"
  resetForm()
  dialogVisible.value = true
}

const openEditDialog = (row: FutureFundamentalAnalysis) => {
  dialogMode.value = "edit"
  form.analysis_id = row.analysis_id
  form.product_id = row.product_id
  form.report_id = row.report_id
  form.supply_side = row.supply_side ?? ""
  form.demand_side = row.demand_side ?? ""
  form.inventory_side = row.inventory_side ?? ""
  form.industry_profit = row.industry_profit ?? ""
  form.substitution_linkage = row.substitution_linkage ?? ""
  form.policy_macro = row.policy_macro ?? ""
  form.conclusion = row.conclusion ?? ""
  formRef.value?.clearValidate()
  dialogVisible.value = true
}

const openUploadDialog = () => {
  resetReportUploadForm()
  reportUploadDialogVisible.value = true
}

const trimToNull = (value: string) => {
  const cleaned = value.trim()
  return cleaned ? cleaned : null
}

const submitForm = async () => {
  if (!formRef.value) {
    return
  }
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid || form.product_id === null || form.report_id === null) {
    return
  }

  const payload = {
    product_id: form.product_id,
    report_id: form.report_id,
    supply_side: trimToNull(form.supply_side),
    demand_side: trimToNull(form.demand_side),
    inventory_side: trimToNull(form.inventory_side),
    industry_profit: trimToNull(form.industry_profit),
    substitution_linkage: trimToNull(form.substitution_linkage),
    policy_macro: trimToNull(form.policy_macro),
    conclusion: trimToNull(form.conclusion),
  }

  submitting.value = true
  try {
    if (dialogMode.value === "create") {
      await createFutureFundamentalAnalysisApi(payload)
      ElMessage.success("新增分析成功")
    } else if (form.analysis_id) {
      await updateFutureFundamentalAnalysisApi({
        analysis_id: form.analysis_id,
        ...payload,
      })
      ElMessage.success("更新分析成功")
    }
    dialogVisible.value = false
    await loadAnalyses()
  } catch {
    ElMessage.error(dialogMode.value === "create" ? "新增分析失败" : "更新分析失败")
  } finally {
    submitting.value = false
  }
}

const handleReportFileChange = (uploadFile: UploadFile) => {
  reportUploadForm.file = uploadFile.raw ?? null
}

const handleReportFileRemove = () => {
  reportUploadForm.file = null
}

const beforeSelectReportFile = (file: File) => {
  const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")
  if (!isPdf) {
    ElMessage.error("只支持上传PDF文件")
    return false
  }
  reportUploadForm.file = file
  return false
}

const submitReportUpload = async () => {
  if (!reportUploadFormRef.value) {
    return
  }
  const valid = await reportUploadFormRef.value.validate().catch(() => false)
  if (!valid || !reportUploadForm.file) {
    return
  }

  reportSubmitting.value = true
  try {
    await uploadFutureReportDocumentApi({
      published_at: reportUploadForm.published_at,
      report_source: reportUploadForm.report_source.trim(),
      file: reportUploadForm.file,
    })
    ElMessage.success("研报上传成功")
    reportUploadDialogVisible.value = false
    await loadReports()
  } catch {
    ElMessage.error("研报上传失败")
  } finally {
    reportSubmitting.value = false
  }
}

const handleDeleteReport = async (row: FutureReportDocument) => {
  await ElMessageBox.confirm(`确认删除研报《${row.report_name}》吗？`, "删除研报", {
    type: "warning",
  })
  try {
    await deleteFutureReportDocumentApi(row.report_id)
    ElMessage.success("研报已删除")
    await Promise.all([loadReports(), loadAnalyses()])
  } catch {
    ElMessage.error("删除研报失败")
  }
}

const handleDeleteAnalysis = async (row: FutureFundamentalAnalysis) => {
  await ElMessageBox.confirm(
    `确认删除 ${row.product_display_name} - ${row.report_name} 的分析记录吗？`,
    "删除分析",
    { type: "warning" },
  )
  try {
    await deleteFutureFundamentalAnalysisApi(row.analysis_id)
    ElMessage.success("分析记录已删除")
    await loadAnalyses()
  } catch {
    ElMessage.error("删除分析记录失败")
  }
}

const openReport = (row: FutureReportDocument | FutureFundamentalAnalysis) => {
  const path = "storage_path" in row ? row.storage_path : row.report_storage_path
  const url = resolveFutureReportPdfUrl(path)
  if (url) {
    window.open(url, "_blank")
  }
}

const formatDateTime = (_row: unknown, _column: unknown, value: string) => {
  return formatDateTimeByDayjs(value)
}

const formatFileSize = (size: number) => {
  if (size >= 1024 * 1024) {
    return `${(size / (1024 * 1024)).toFixed(2)} MB`
  }
  if (size >= 1024) {
    return `${(size / 1024).toFixed(1)} KB`
  }
  return `${size} B`
}

onMounted(() => {
  void Promise.all([loadProducts(), loadReports(), loadAnalyses()])
})
</script>

<template>
  <div class="pageBox fundamental-analysis-page">
    <div class="page-header">
      <div>
        <h2 class="title">基本面分析</h2>
        <p class="subtitle">左侧维护PDF研报文件，右侧手工沉淀结构化的基本面分析结果。</p>
      </div>
      <el-button type="primary" @click="openCreateDialog">新增分析</el-button>
    </div>

    <div class="content-grid">
      <section class="panel left-panel">
        <div class="panel-header">
          <div>
            <h3>研报上传</h3>
            <p>PDF原件直接保存到 `/storage/future_reports`，上传时补充发布时间和来源。</p>
          </div>
          <el-button type="primary" @click="openUploadDialog">上传研报</el-button>
        </div>

        <el-table
          v-loading="reportLoading"
          :data="reports"
          border
          row-key="report_id"
          empty-text="暂无研报"
          height="620"
        >
          <el-table-column prop="report_name" label="研报" min-width="220">
            <template #default="{ row }">
              <el-button type="primary" link @click="openReport(row)">{{ row.report_name }}</el-button>
              <div class="meta-text">{{ row.original_filename }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="report_source" label="来源" min-width="140" />
          <el-table-column prop="published_at" label="发布时间" min-width="180" :formatter="formatDateTime" />
          <el-table-column label="大小" width="110">
            <template #default="{ row }">
              {{ formatFileSize(row.file_size) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="openReport(row)">打开</el-button>
              <el-button type="danger" link @click="handleDeleteReport(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section class="panel right-panel">
        <div class="panel-header">
          <div>
            <h3>分析结果表</h3>
            <p>先手工录入结构化观点，后续再接JSON自动回填。</p>
          </div>
        </div>

        <el-table
          v-loading="analysisLoading"
          :data="analyses"
          border
          row-key="analysis_id"
          empty-text="暂无基本面分析"
          height="620"
        >
          <el-table-column label="产品" min-width="160" fixed="left">
            <template #default="{ row }">
              <div>{{ row.product_display_name }}</div>
              <div class="meta-text">{{ row.product_code }}</div>
            </template>
          </el-table-column>
          <el-table-column label="研报" min-width="220">
            <template #default="{ row }">
              <el-button type="primary" link @click="openReport(row)">{{ row.report_name }}</el-button>
            </template>
          </el-table-column>
          <el-table-column prop="supply_side" label="供给端" min-width="220" show-overflow-tooltip />
          <el-table-column prop="demand_side" label="需求端" min-width="220" show-overflow-tooltip />
          <el-table-column prop="inventory_side" label="库存端" min-width="220" show-overflow-tooltip />
          <el-table-column prop="industry_profit" label="产业利润" min-width="220" show-overflow-tooltip />
          <el-table-column prop="substitution_linkage" label="替代与联动" min-width="220" show-overflow-tooltip />
          <el-table-column prop="policy_macro" label="政策与宏观" min-width="220" show-overflow-tooltip />
          <el-table-column prop="conclusion" label="结论" min-width="240" show-overflow-tooltip />
          <el-table-column prop="updated_at" label="更新时间" min-width="180" :formatter="formatDateTime" />
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="openEditDialog(row)">编辑</el-button>
              <el-button type="danger" link @click="handleDeleteAnalysis(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </div>

    <el-dialog v-model="reportUploadDialogVisible" title="上传研报" width="32rem" @closed="resetReportUploadForm">
      <el-form ref="reportUploadFormRef" :model="reportUploadForm" :rules="reportUploadRules" label-width="6rem">
        <el-form-item label="发布时间" prop="published_at">
          <el-date-picker
            v-model="reportUploadForm.published_at"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="请选择发布时间"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="来源" prop="report_source">
          <el-input v-model.trim="reportUploadForm.report_source" placeholder="例如：国泰君安期货" />
        </el-form-item>
        <el-form-item label="上传文件" prop="file">
          <el-upload
            :auto-upload="false"
            :limit="1"
            accept=".pdf,application/pdf"
            :before-upload="beforeSelectReportFile"
            :on-change="handleReportFileChange"
            :on-remove="handleReportFileRemove"
          >
            <el-button type="primary">选择PDF</el-button>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reportUploadDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="reportSubmitting" @click="submitReportUpload">上传</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="56rem" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="7rem">
        <div class="dialog-grid">
          <el-form-item label="产品" prop="product_id">
            <el-select v-model="form.product_id" placeholder="请选择产品" filterable>
              <el-option
                v-for="item in products"
                :key="item.product_id"
                :label="`${item.product_code} / ${item.display_name}`"
                :value="item.product_id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="研报" prop="report_id">
            <el-select v-model="form.report_id" placeholder="请选择研报" filterable>
              <el-option
                v-for="item in reports"
                :key="item.report_id"
                :label="`${item.report_name} / ${item.report_source}`"
                :value="item.report_id"
              />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="供给端">
          <el-input v-model="form.supply_side" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="需求端">
          <el-input v-model="form.demand_side" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="库存端">
          <el-input v-model="form.inventory_side" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="产业利润">
          <el-input v-model="form.industry_profit" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="替代与联动">
          <el-input v-model="form.substitution_linkage" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="政策与宏观">
          <el-input v-model="form.policy_macro" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="结论">
          <el-input v-model="form.conclusion" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="less" scoped>
.fundamental-analysis-page {
  padding: 16px;
}

.page-header,
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.page-header {
  margin-bottom: 16px;
}

.title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.subtitle,
.panel-header p,
.meta-text {
  margin: 6px 0 0;
  color: #909399;
  font-size: 13px;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(340px, 0.9fr) minmax(0, 1.6fr);
  gap: 16px;
}

.panel {
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  background: #fff;
  min-width: 0;
}

.panel-header {
  margin-bottom: 16px;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.dialog-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

@media (max-width: 1200px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-header,
  .panel-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .dialog-grid {
    grid-template-columns: 1fr;
  }
}
</style>
