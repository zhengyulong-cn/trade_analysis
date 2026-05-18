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
import { buildFundamentalAnalysisPrompt } from "@/prompts/fundamentalAnalysisPrompt"
import { formatDateTime as formatDateTimeByDayjs } from "@/utils/date"
import { ElMessage, ElMessageBox, type FormInstance, type FormRules, type UploadFile } from "element-plus"
import { computed, onMounted, reactive, ref, watch } from "vue"

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

interface AnalysisJsonPayload {
  product_code: string
  product_name: string
  supply_side: string
  demand_side: string
  inventory_side: string
  industry_profit: string
  substitution_linkage: string
  policy_macro: string
  conclusion: string
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
const viewDialogVisible = ref(false)
const viewingAnalysis = ref<FutureFundamentalAnalysis | null>(null)

const reportUploadDialogVisible = ref(false)
const reportUploadFormRef = ref<FormInstance>()

const activeAnalysisMode = ref<"fields" | "json">("fields")
const analysisJsonText = ref("")
const analysisJsonError = ref("")
let syncingFromFields = false
let syncingFromJson = false

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

const selectedProduct = computed(() => {
  return products.value.find((item) => item.product_id === form.product_id) ?? null
})

const selectedReport = computed(() => {
  return reports.value.find((item) => item.report_id === form.report_id) ?? null
})

const buildAnalysisJsonPayload = (): AnalysisJsonPayload => ({
  product_code: selectedProduct.value?.product_code ?? "",
  product_name: selectedProduct.value?.display_name ?? "",
  supply_side: form.supply_side,
  demand_side: form.demand_side,
  inventory_side: form.inventory_side,
  industry_profit: form.industry_profit,
  substitution_linkage: form.substitution_linkage,
  policy_macro: form.policy_macro,
  conclusion: form.conclusion,
})

const syncJsonFromForm = () => {
  syncingFromFields = true
  analysisJsonError.value = ""
  analysisJsonText.value = JSON.stringify(buildAnalysisJsonPayload(), null, 2)
  syncingFromFields = false
}

const applyJsonToForm = (payload: Partial<AnalysisJsonPayload>) => {
  syncingFromJson = true
  form.supply_side = typeof payload.supply_side === "string" ? payload.supply_side : ""
  form.demand_side = typeof payload.demand_side === "string" ? payload.demand_side : ""
  form.inventory_side = typeof payload.inventory_side === "string" ? payload.inventory_side : ""
  form.industry_profit = typeof payload.industry_profit === "string" ? payload.industry_profit : ""
  form.substitution_linkage = typeof payload.substitution_linkage === "string" ? payload.substitution_linkage : ""
  form.policy_macro = typeof payload.policy_macro === "string" ? payload.policy_macro : ""
  form.conclusion = typeof payload.conclusion === "string" ? payload.conclusion : ""

  const jsonProductCode =
    typeof payload.product_code === "string" ? payload.product_code.trim().toUpperCase() : ""
  if (jsonProductCode) {
    const matchedProduct = products.value.find((item) => item.product_code.toUpperCase() === jsonProductCode)
    if (matchedProduct) {
      form.product_id = matchedProduct.product_id
    }
  }

  syncingFromJson = false
  analysisJsonError.value = ""
}

watch(
  () => [
    form.product_id,
    form.supply_side,
    form.demand_side,
    form.inventory_side,
    form.industry_profit,
    form.substitution_linkage,
    form.policy_macro,
    form.conclusion,
  ],
  () => {
    if (syncingFromJson) {
      return
    }
    syncJsonFromForm()
  },
  { deep: true },
)

watch(
  analysisJsonText,
  (value) => {
    if (syncingFromFields) {
      return
    }
    const trimmed = value.trim()
    if (!trimmed) {
      analysisJsonError.value = ""
      return
    }
    try {
      const parsed = JSON.parse(trimmed) as Partial<AnalysisJsonPayload>
      applyJsonToForm(parsed)
    } catch {
      analysisJsonError.value = "JSON格式不合法，暂未回填字段"
    }
  },
)

const sortProducts = (items: FutureProduct[]) => {
  return [...items].sort((first, second) => first.product_code.localeCompare(second.product_code, "zh-CN"))
}

const sortReports = (items: FutureReportDocument[]) => {
  return [...items].sort((first, second) => second.published_at.localeCompare(first.published_at))
}

const loadProducts = async () => {
  try {
    products.value = sortProducts(await getFutureProductList())
    syncJsonFromForm()
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
  activeAnalysisMode.value = "fields"
  analysisJsonError.value = ""
  formRef.value?.clearValidate()
  syncJsonFromForm()
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
  activeAnalysisMode.value = "fields"
  analysisJsonError.value = ""
  formRef.value?.clearValidate()
  syncJsonFromForm()
  dialogVisible.value = true
}

const openViewDialog = (row: FutureFundamentalAnalysis) => {
  viewingAnalysis.value = row
  viewDialogVisible.value = true
}

const openUploadDialog = () => {
  resetReportUploadForm()
  reportUploadDialogVisible.value = true
}

const handleCopyPrompt = async () => {
  if (!selectedProduct.value) {
    ElMessage.warning("请先选择产品")
    return
  }

  const prompt = buildFundamentalAnalysisPrompt({
    productCode: selectedProduct.value.product_code,
    productName: selectedProduct.value.display_name,
    aliasNames: selectedProduct.value.alias_names,
    reportName: selectedReport.value?.report_name,
    reportSource: selectedReport.value?.report_source,
    publishedAt: selectedReport.value?.published_at,
  })

  try {
    await navigator.clipboard.writeText(prompt)
    ElMessage.success("Prompt已复制")
  } catch {
    ElMessage.error("复制失败，请检查浏览器权限")
  }
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

const displayFieldText = (value?: string | null) => {
  const cleaned = typeof value === "string" ? value.trim() : ""
  return cleaned || "未填写"
}

onMounted(() => {
  void Promise.all([loadProducts(), loadReports(), loadAnalyses()])
  syncJsonFromForm()
})
</script>

<template>
  <div class="pageBox fundamental-analysis-page">
    <div class="page-header">
      <div>
        <h2 class="title">基本面分析</h2>
      </div>
    </div>

    <div class="content-grid">
      <section class="panel left-panel">
        <div class="panel-header">
          <div>
            <h3>研报上传</h3>
          </div>
          <el-button type="primary" @click="openUploadDialog">上传研报</el-button>
        </div>

        <el-table
          v-loading="reportLoading"
          :data="reports"
          border
          row-key="report_id"
          empty-text="暂无研报"
          height="40rem"
        >
          <el-table-column prop="report_name" label="研报" min-width="220">
            <template #default="{ row }">
              <el-button type="primary" link @click="openReport(row)">{{ row.report_name }}</el-button>
              <div class="meta-text">{{ row.original_filename }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="published_at" label="发布时间" min-width="180" :formatter="formatDateTime" />
          <el-table-column prop="report_source" label="来源" min-width="140" />
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
          </div>
          <el-button type="primary" @click="openCreateDialog">新增分析</el-button>
        </div>

        <el-table
          v-loading="analysisLoading"
          :data="analyses"
          border
          row-key="analysis_id"
          empty-text="暂无基本面分析"
          height="40rem"
        >
          <el-table-column label="产品" min-width="80" fixed="left">
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
          <el-table-column label="操作" width="190" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="openViewDialog(row)">查看</el-button>
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

        <div class="prompt-toolbar">
          <div class="prompt-toolbar-text">
            选择好产品和研报后，可一键复制发给 DeepSeek 的分析 prompt。
          </div>
          <el-button plain type="primary" @click="handleCopyPrompt">一键复制 Prompt</el-button>
        </div>

        <el-tabs v-model="activeAnalysisMode" class="analysis-mode-tabs">
          <el-tab-pane label="字段模式" name="fields">
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
          </el-tab-pane>

          <el-tab-pane label="JSON模式" name="json">
            <div class="json-mode-tip">
              粘贴合法JSON后，字段模式会自动回填；字段模式修改内容后，这里也会自动同步。
            </div>
            <el-input v-model="analysisJsonText" type="textarea" :rows="20" placeholder="请粘贴JSON" />
            <div class="json-mode-error" v-if="analysisJsonError">{{ analysisJsonError }}</div>
          </el-tab-pane>
        </el-tabs>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="viewDialogVisible" title="分析详情" width="62rem">
      <div v-if="viewingAnalysis" class="analysis-detail">
        <div class="detail-hero">
          <div class="detail-main">
            <div class="detail-product">
              {{ viewingAnalysis.product_display_name }}
              <span class="detail-product-code">{{ viewingAnalysis.product_code }}</span>
            </div>
            <div class="detail-report-row">
              <span class="detail-report-name">{{ viewingAnalysis.report_name }}</span>
              <el-button type="primary" link @click="openReport(viewingAnalysis)">查看原PDF</el-button>
            </div>
          </div>
          <div class="detail-meta">
            <div>创建时间：{{ formatDateTime(undefined, undefined, viewingAnalysis.create_at) }}</div>
            <div>更新时间：{{ formatDateTime(undefined, undefined, viewingAnalysis.updated_at) }}</div>
          </div>
        </div>

        <div class="detail-grid">
          <section class="detail-card">
            <h4>供给端</h4>
            <p>{{ displayFieldText(viewingAnalysis.supply_side) }}</p>
          </section>
          <section class="detail-card">
            <h4>需求端</h4>
            <p>{{ displayFieldText(viewingAnalysis.demand_side) }}</p>
          </section>
          <section class="detail-card">
            <h4>库存端</h4>
            <p>{{ displayFieldText(viewingAnalysis.inventory_side) }}</p>
          </section>
          <section class="detail-card">
            <h4>产业利润</h4>
            <p>{{ displayFieldText(viewingAnalysis.industry_profit) }}</p>
          </section>
          <section class="detail-card">
            <h4>替代与联动</h4>
            <p>{{ displayFieldText(viewingAnalysis.substitution_linkage) }}</p>
          </section>
          <section class="detail-card">
            <h4>政策与宏观</h4>
            <p>{{ displayFieldText(viewingAnalysis.policy_macro) }}</p>
          </section>
        </div>

        <section class="detail-card detail-conclusion">
          <h4>结论</h4>
          <p>{{ displayFieldText(viewingAnalysis.conclusion) }}</p>
        </section>
      </div>
      <template #footer>
        <el-button @click="viewDialogVisible = false">关闭</el-button>
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

.analysis-mode-tabs {
  margin-top: 4px;
}

.prompt-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 4px 0 12px;
  padding: 12px 14px;
  border-radius: 10px;
  background: #f7f9fc;
  border: 1px solid #e7ecf3;
}

.prompt-toolbar-text {
  color: #606266;
  font-size: 13px;
}

.json-mode-tip {
  margin-bottom: 12px;
  color: #606266;
  font-size: 13px;
}

.json-mode-error {
  margin-top: 8px;
  color: #f56c6c;
  font-size: 13px;
}

.analysis-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-hero {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding: 18px 20px;
  border-radius: 14px;
  background: linear-gradient(135deg, #f7fbff 0%, #eef5ff 100%);
  border: 1px solid #dbe7ff;
}

.detail-main {
  min-width: 0;
}

.detail-product {
  font-size: 22px;
  font-weight: 700;
  color: #1f2d3d;
}

.detail-product-code {
  margin-left: 10px;
  font-size: 14px;
  font-weight: 600;
  color: #4e6ef2;
  background: rgba(78, 110, 242, 0.1);
  border-radius: 999px;
  padding: 4px 10px;
  vertical-align: middle;
}

.detail-report-row {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.detail-report-name,
.detail-meta {
  color: #606266;
  font-size: 13px;
  line-height: 1.8;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.detail-card {
  padding: 16px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #ebeef5;
  box-shadow: 0 8px 24px rgba(31, 45, 61, 0.06);
}

.detail-card h4 {
  margin: 0 0 10px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.detail-card p {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.75;
  color: #4f5b66;
  font-size: 14px;
}

.detail-conclusion {
  background: linear-gradient(180deg, #fffaf2 0%, #fffdf8 100%);
  border-color: #f2dfb1;
}


@media (max-width: 1200px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .detail-grid {
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

  .prompt-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .detail-hero {
    flex-direction: column;
  }
}
</style>
