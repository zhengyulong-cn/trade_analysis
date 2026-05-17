<script lang="ts" setup>
import {
  getFutureContractList,
  getFutureContractPromptProfileList,
  getReportDocumentListApi,
  getSingleContractReportAnalysisItemApi,
  getSingleContractReportAnalysisListApi,
  runSingleContractReportAnalysisApi,
  type FutureContract,
  type FutureContractPromptProfile,
  type ReportDocumentListItem,
  type SingleContractReportAnalysis,
  type SingleContractReportAnalysisListItem,
} from '@/api/modules'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { formatDateTime } from '@/utils/date'

const loading = ref(false)
const running = ref(false)
const detailLoading = ref(false)
const contracts = ref<FutureContract[]>([])
const promptProfiles = ref<FutureContractPromptProfile[]>([])
const reports = ref<ReportDocumentListItem[]>([])
const analysisList = ref<SingleContractReportAnalysisListItem[]>([])
const currentAnalysis = ref<SingleContractReportAnalysis | null>(null)
const selectedContractId = ref<number | undefined>()
const selectedReportId = ref<number | undefined>()

const profileMap = computed(() => new Map(promptProfiles.value.map((item) => [item.contract_id, item])))

const selectedProfile = computed(() => {
  if (!selectedContractId.value) {
    return null
  }
  return profileMap.value.get(selectedContractId.value) ?? null
})

const selectedReport = computed(() => {
  if (!selectedReportId.value) {
    return null
  }
  return reports.value.find((item) => item.report_id === selectedReportId.value) ?? null
})

const canRun = computed(() => Boolean(selectedContractId.value && selectedReportId.value))

const stanceLabelMap: Record<string, string> = {
  bullish: '偏多',
  bearish: '偏空',
  neutral: '中性',
  mixed: '多空交织',
}

const relevanceLabelMap: Record<string, string> = {
  high: '高相关',
  medium: '中相关',
  low: '低相关',
  none: '无明显相关',
}

const loadBaseData = async () => {
  loading.value = true
  try {
    const [contractData, profileData, reportData, analysisData] = await Promise.all([
      getFutureContractList(),
      getFutureContractPromptProfileList(),
      getReportDocumentListApi(),
      getSingleContractReportAnalysisListApi(),
    ])
    contracts.value = contractData
    promptProfiles.value = profileData
    reports.value = reportData
    analysisList.value = analysisData
    if (analysisData.length > 0) {
      await loadAnalysisDetail(analysisData[0].analysis_id)
    }
  } catch {
    ElMessage.error('获取页面数据失败')
  } finally {
    loading.value = false
  }
}

const loadAnalysisList = async () => {
  try {
    analysisList.value = await getSingleContractReportAnalysisListApi({
      contract_id: selectedContractId.value,
      report_id: selectedReportId.value,
    })
  } catch {
    ElMessage.error('获取分析记录失败')
  }
}

const loadAnalysisDetail = async (analysisId: number) => {
  detailLoading.value = true
  try {
    currentAnalysis.value = await getSingleContractReportAnalysisItemApi(analysisId)
  } catch {
    ElMessage.error('获取分析详情失败')
  } finally {
    detailLoading.value = false
  }
}

const handleRunAnalysis = async () => {
  if (!selectedContractId.value || !selectedReportId.value) {
    ElMessage.warning('请先选择合约和研报')
    return
  }
  if (!selectedProfile.value) {
    ElMessage.warning('该合约还没有配置 AI 画像')
    return
  }
  if (selectedProfile.value.is_active !== 1) {
    ElMessage.warning('该合约的 AI 画像当前未启用')
    return
  }

  running.value = true
  try {
    const result = await runSingleContractReportAnalysisApi({
      contract_id: selectedContractId.value,
      report_id: selectedReportId.value,
    })
    currentAnalysis.value = result
    await loadAnalysisList()
    ElMessage.success('分析完成')
  } catch (error) {
    const response = error as { data?: { detail?: string } }
    ElMessage.error(response.data?.detail || '分析失败')
  } finally {
    running.value = false
  }
}

onMounted(() => {
  void loadBaseData()
})
</script>

<template>
  <div v-loading="loading" class="pageBox single-contract-report-analysis">
    <div class="page-header">
      <div>
        <h2 class="title">单品种研报分析</h2>
        <p class="subtitle">一个品种配一套 AI 画像，每次拿一篇研报做一次定向分析，并保存分析记录。</p>
      </div>
    </div>

    <div class="selector-card">
      <div class="selector-grid">
        <el-form-item label="目标合约" class="selector-item">
          <el-select v-model="selectedContractId" filterable placeholder="请选择合约">
            <el-option
              v-for="item in contracts"
              :key="item.contract_id"
              :label="`${item.symbol} ${item.name}`"
              :value="item.contract_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="研报" class="selector-item">
          <el-select v-model="selectedReportId" filterable placeholder="请选择研报">
            <el-option
              v-for="item in reports"
              :key="item.report_id"
              :label="`${item.original_name}${item.source ? `（${item.source}）` : ''}`"
              :value="item.report_id"
            />
          </el-select>
        </el-form-item>
        <div class="selector-actions">
          <el-button type="primary" :loading="running" :disabled="!canRun" @click="handleRunAnalysis">
            开始分析
          </el-button>
          <el-button @click="loadAnalysisList">刷新记录</el-button>
        </div>
      </div>
    </div>

    <div class="info-grid">
      <div class="info-card">
        <h3>AI画像摘要</h3>
        <template v-if="selectedProfile">
          <div class="meta-line"><strong>状态：</strong>{{ selectedProfile.is_active === 1 ? '启用' : '停用' }}</div>
          <div class="meta-line"><strong>关注维度：</strong>{{ selectedProfile.focus_dimensions.join('、') || '-' }}</div>
          <div class="meta-line"><strong>分析风格：</strong>{{ selectedProfile.analysis_style || '-' }}</div>
          <div class="meta-line"><strong>额外提示：</strong>{{ selectedProfile.extra_instruction || '-' }}</div>
          <div class="meta-line"><strong>输出偏好：</strong>{{ selectedProfile.output_preference || '-' }}</div>
        </template>
        <div v-else class="placeholder-text">当前合约尚未配置 AI 画像。</div>
      </div>

      <div class="info-card">
        <h3>研报摘要</h3>
        <template v-if="selectedReport">
          <div class="meta-line"><strong>标题：</strong>{{ selectedReport.title || selectedReport.original_name }}</div>
          <div class="meta-line"><strong>来源：</strong>{{ selectedReport.source || '-' }}</div>
          <div class="meta-line"><strong>发布日期：</strong>{{ selectedReport.published_at || '-' }}</div>
          <div class="meta-line"><strong>上传时间：</strong>{{ formatDateTime(selectedReport.create_at) }}</div>
        </template>
        <div v-else class="placeholder-text">请选择一篇研报作为分析输入。</div>
      </div>
    </div>

    <div class="result-layout">
      <div class="result-panel">
        <h3>分析结果</h3>
        <div v-loading="detailLoading" class="result-body">
          <template v-if="currentAnalysis?.result_json">
            <div class="result-summary">
              <el-tag effect="plain">{{ relevanceLabelMap[currentAnalysis.result_json.relevance] }}</el-tag>
              <el-tag type="success" effect="plain">{{ stanceLabelMap[currentAnalysis.result_json.stance] }}</el-tag>
              <el-tag type="info" effect="plain">置信度 {{ currentAnalysis.result_json.confidence }}</el-tag>
              <el-tag type="warning" effect="plain">{{ currentAnalysis.result_json.horizon }}</el-tag>
            </div>
            <div class="result-section">
              <strong>结论摘要</strong>
              <p>{{ currentAnalysis.result_json.summary }}</p>
            </div>
            <div class="result-section">
              <strong>核心驱动</strong>
              <ul>
                <li v-for="item in currentAnalysis.result_json.drivers" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div class="result-section">
              <strong>主要风险</strong>
              <ul>
                <li v-for="item in currentAnalysis.result_json.risks" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div class="result-section">
              <strong>依据要点</strong>
              <ul>
                <li v-for="item in currentAnalysis.result_json.evidence" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div class="result-section">
              <strong>命中片段</strong>
              <div
                v-for="(item, index) in currentAnalysis.matched_snippets"
                :key="`${currentAnalysis.analysis_id}-${index}`"
                class="snippet-block"
              >
                {{ item }}
              </div>
            </div>
          </template>
          <div v-else class="placeholder-text">还没有分析结果，先选择合约和研报后执行一次分析。</div>
        </div>
      </div>

      <div class="history-panel">
        <h3>分析记录</h3>
        <el-table
          :data="analysisList"
          border
          row-key="analysis_id"
          height="620"
          empty-text="暂无分析记录"
        >
          <el-table-column prop="analysis_id" label="ID" width="80" />
          <el-table-column label="品种" min-width="150">
            <template #default="{ row }">
              {{ row.contract_symbol }} {{ row.contract_name }}
            </template>
          </el-table-column>
          <el-table-column prop="report_title" label="研报" min-width="220" show-overflow-tooltip />
          <el-table-column label="观点" width="100">
            <template #default="{ row }">
              {{ row.result_json ? stanceLabelMap[row.result_json.stance] : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="时间" min-width="170">
            <template #default="{ row }">
              {{ formatDateTime(row.create_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="loadAnalysisDetail(row.analysis_id)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<style lang="less" scoped>
.single-contract-report-analysis {
  padding: 16px;
}

.page-header {
  margin-bottom: 16px;
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

.selector-card,
.info-card,
.result-panel,
.history-panel {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
}

.selector-card {
  padding: 16px;
  margin-bottom: 16px;
}

.selector-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
  gap: 16px;
  align-items: end;
}

.selector-item {
  margin-bottom: 0;
}

.selector-actions {
  display: flex;
  gap: 12px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.info-card,
.result-panel,
.history-panel {
  padding: 16px;
}

.info-card h3,
.result-panel h3,
.history-panel h3 {
  margin: 0 0 12px;
  font-size: 16px;
}

.meta-line {
  line-height: 1.8;
  color: #303133;
}

.result-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(420px, 1fr);
  gap: 16px;
}

.result-body {
  min-height: 620px;
}

.result-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.result-section {
  margin-bottom: 18px;
}

.result-section p {
  margin: 8px 0 0;
  line-height: 1.8;
}

.result-section ul {
  margin: 8px 0 0;
  padding-left: 18px;
}

.result-section li {
  line-height: 1.8;
}

.snippet-block {
  margin-top: 8px;
  padding: 10px 12px;
  background: #f7f9fc;
  border-radius: 8px;
  line-height: 1.8;
  color: #303133;
}

.placeholder-text {
  color: #909399;
}

@media (max-width: 1200px) {
  .result-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .selector-grid,
  .info-grid {
    grid-template-columns: 1fr;
  }

  .selector-actions {
    justify-content: flex-end;
  }
}
</style>
