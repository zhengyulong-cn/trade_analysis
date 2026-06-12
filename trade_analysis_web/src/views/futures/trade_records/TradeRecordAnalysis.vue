<script lang="ts" setup>
import {
  getTradeAccountListApi,
  getTradeRecordColumnListApi,
  getTradeRecordListApi,
  type TradeAccount,
  type TradeRecord,
  type TradeRecordColumn,
  type TradeRecordColumnOption,
} from "@/api/modules"
import { ElMessage } from "element-plus"
import { computed, onMounted, ref } from "vue"

type PeriodType = "day" | "week" | "half_month" | "month"

interface AnalysisRecord {
  record: TradeRecord
  accountId: string
  closeTime: Date
  operatePnl: number
  fee: number
  realPnl: number
}

interface Metrics {
  tradeCount: number
  winCount: number
  lossCount: number
  winRate: number
  totalPnl: number
  totalFee: number
  avgPnl: number
  avgWin: number | null
  avgLoss: number | null
  profitLossRatio: number | null
  maxWin: number | null
  maxLoss: number | null
  activeDayCount: number
  avgTradesPerDay: number
  maxConsecutiveLosses: number
}

interface PeriodRow extends Metrics {
  periodKey: string
  periodLabel: string
}

interface FactorRow extends Metrics {
  factorKey: string
  factorLabel: string
  factorValue: string
  factorValueLabel: string
  sampleWarning: boolean
}

interface AccountRow extends Metrics {
  accountId: string
  accountName: string
  accountType: string
}

const props = defineProps<{
  handleModeChange: (mode: string | number | boolean) => void
}>()

const loading = ref(false)
const records = ref<TradeRecord[]>([])
const columns = ref<TradeRecordColumn[]>([])
const accounts = ref<TradeAccount[]>([])
const selectedAccountId = ref("all")
const selectedPeriodType = ref<PeriodType>("day")
const selectedFactorKey = ref("")

const enabledColumns = computed(() => columns.value.filter((item) => item.is_enabled))

const accountColumn = computed(() =>
  enabledColumns.value.find(
    (column) =>
      column.data_type === "single_select" &&
      String(column.option_source_config?.source ?? "") === "trade_accounts",
  ),
)

const operatePnlColumn = computed(() => findColumn(["operate_pnl", "operation_pnl"], ["操作盈亏"]))
const feeColumn = computed(() => findColumn(["fee"], ["手续费"]))
const closeTimeColumn = computed(() => findColumn(["close_time"], ["平仓时间"]))
const closePriceColumn = computed(() => findColumn(["close_price"], ["平仓价格"]))

const accountOptions = computed(() => [
  { label: "全部账户", value: "all" },
  ...accounts.value.map((account) => ({
    label: `${account.account_name}（${account.account_type === "real" ? "实盘" : "模拟"}）`,
    value: String(account.account_id),
  })),
  { label: "未绑定账户", value: "__unbound__" },
])

const factorColumns = computed(() =>
  enabledColumns.value.filter((column) => {
    if (column.column_id === accountColumn.value?.column_id) {
      return false
    }
    return ["single_select", "multi_select", "bool"].includes(column.data_type)
  }),
)

const analysisReady = computed(
  () =>
    Boolean(accountColumn.value) &&
    Boolean(operatePnlColumn.value) &&
    Boolean(feeColumn.value) &&
    Boolean(closeTimeColumn.value) &&
    Boolean(closePriceColumn.value),
)

const missingMessages = computed(() => {
  const messages: string[] = []
  if (!accountColumn.value) {
    messages.push("未配置账户列")
  }
  if (!operatePnlColumn.value) {
    messages.push("未配置操作盈亏列")
  }
  if (!feeColumn.value) {
    messages.push("未配置手续费列")
  }
  if (!closeTimeColumn.value) {
    messages.push("未配置平仓时间列")
  }
  if (!closePriceColumn.value) {
    messages.push("未配置平仓价格列")
  }
  return messages
})

const accountMap = computed(() => new Map(accounts.value.map((account) => [String(account.account_id), account])))

const closedAnalysisRecords = computed<AnalysisRecord[]>(() => {
  if (!analysisReady.value || !accountColumn.value || !operatePnlColumn.value || !feeColumn.value || !closeTimeColumn.value || !closePriceColumn.value) {
    return []
  }

  return records.value
    .map((record) => {
      const closeTimeValue = record.data_json[closeTimeColumn.value!.column_key]
      const closePriceValue = record.data_json[closePriceColumn.value!.column_key]
      if (isBlank(closeTimeValue) || isBlank(closePriceValue)) {
        return null
      }

      const closeTime = parseDate(closeTimeValue)
      const operatePnl = toNumber(record.data_json[operatePnlColumn.value!.column_key])
      if (!closeTime || operatePnl === null) {
        return null
      }

      const fee = toNumber(record.data_json[feeColumn.value!.column_key]) ?? 0
      const rawAccountId = record.data_json[accountColumn.value!.column_key]
      const accountId = isBlank(rawAccountId) ? "__unbound__" : String(rawAccountId)

      return {
        record,
        accountId,
        closeTime,
        operatePnl,
        fee,
        realPnl: operatePnl - fee,
      } satisfies AnalysisRecord
    })
    .filter((item): item is AnalysisRecord => Boolean(item))
})

const selectedRecords = computed(() => {
  if (selectedAccountId.value === "all") {
    return closedAnalysisRecords.value
  }
  return closedAnalysisRecords.value.filter((item) => item.accountId === selectedAccountId.value)
})

const overviewMetrics = computed(() => calculateMetrics(selectedRecords.value))
const periodRows = computed(() => buildPeriodRows(selectedRecords.value, selectedPeriodType.value))
const factorRows = computed(() => buildFactorRows(selectedRecords.value, selectedFactorColumn.value))

const accountRows = computed<AccountRow[]>(() => {
  const groups = groupBy(closedAnalysisRecords.value, (item) => item.accountId)
  return [...groups.entries()]
    .map(([accountId, items]) => {
      const account = accountMap.value.get(accountId)
      return {
        accountId,
        accountName: account?.account_name ?? "未绑定账户",
        accountType: account ? (account.account_type === "real" ? "实盘" : "模拟") : "-",
        ...calculateMetrics(items),
      }
    })
    .sort((a, b) => b.totalPnl - a.totalPnl)
})

const selectedFactorColumn = computed(() => {
  if (selectedFactorKey.value) {
    const target = factorColumns.value.find((column) => column.column_key === selectedFactorKey.value)
    if (target) {
      return target
    }
  }
  return factorColumns.value[0] ?? null
})

const selectedAccountLabel = computed(() => {
  if (selectedAccountId.value === "all") {
    return "全部账户"
  }
  if (selectedAccountId.value === "__unbound__") {
    return "未绑定账户"
  }
  return accountMap.value.get(selectedAccountId.value)?.account_name ?? "未知账户"
})

const loadData = async () => {
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
    selectedFactorKey.value = ""
  } catch {
    ElMessage.error("交易记录分析数据加载失败")
  } finally {
    loading.value = false
  }
}

function findColumn(keys: string[], labels: string[]) {
  const normalizedKeys = new Set(keys.map((item) => item.toLowerCase()))
  return (
    enabledColumns.value.find((column) => normalizedKeys.has(column.column_key.toLowerCase())) ??
    enabledColumns.value.find((column) => labels.some((label) => column.column_label.includes(label))) ??
    null
  )
}

function isBlank(value: unknown) {
  return value === null || value === undefined || (typeof value === "string" && !value.trim())
}

function toNumber(value: unknown) {
  if (isBlank(value)) {
    return null
  }
  const numericValue = Number(value)
  return Number.isFinite(numericValue) ? numericValue : null
}

function parseDate(value: unknown) {
  if (value instanceof Date && Number.isFinite(value.getTime())) {
    return value
  }
  const date = new Date(String(value))
  return Number.isFinite(date.getTime()) ? date : null
}

function formatMoney(value: number | null) {
  if (value === null || !Number.isFinite(value)) {
    return "-"
  }
  return value.toFixed(2)
}

function formatRate(value: number) {
  if (!Number.isFinite(value)) {
    return "-"
  }
  return `${(value * 100).toFixed(1)}%`
}

function formatRatio(value: number | null) {
  if (value === null || !Number.isFinite(value)) {
    return "-"
  }
  return value.toFixed(2)
}

function formatDateKey(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

function getWeekInfo(date: Date) {
  const target = new Date(date)
  target.setHours(0, 0, 0, 0)
  const day = target.getDay() || 7
  target.setDate(target.getDate() + 4 - day)
  const yearStart = new Date(target.getFullYear(), 0, 1)
  const week = Math.ceil(((target.getTime() - yearStart.getTime()) / 86400000 + 1) / 7)
  return {
    year: target.getFullYear(),
    week,
  }
}

function getPeriodInfo(date: Date, periodType: PeriodType) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")

  if (periodType === "day") {
    const key = formatDateKey(date)
    return { key, label: key }
  }

  if (periodType === "week") {
    const { year: weekYear, week } = getWeekInfo(date)
    const weekText = String(week).padStart(2, "0")
    return { key: `${weekYear}-W${weekText}`, label: `${weekYear} 第 ${weekText} 周` }
  }

  if (periodType === "half_month") {
    const half = date.getDate() <= 15 ? "H1" : "H2"
    return {
      key: `${year}-${month}-${half}`,
      label: `${year}-${month} ${half === "H1" ? "上半月" : "下半月"}`,
    }
  }

  return { key: `${year}-${month}`, label: `${year}-${month}` }
}

function groupBy<T>(items: T[], getKey: (item: T) => string) {
  const groups = new Map<string, T[]>()
  for (const item of items) {
    const key = getKey(item)
    groups.set(key, [...(groups.get(key) ?? []), item])
  }
  return groups
}

function calculateMetrics(items: AnalysisRecord[]): Metrics {
  const tradeCount = items.length
  const pnlValues = items.map((item) => item.realPnl)
  const winValues = pnlValues.filter((item) => item > 0)
  const lossValues = pnlValues.filter((item) => item < 0)
  const totalPnl = pnlValues.reduce((sum, item) => sum + item, 0)
  const totalFee = items.reduce((sum, item) => sum + item.fee, 0)
  const avgWin = winValues.length ? average(winValues) : null
  const avgLoss = lossValues.length ? average(lossValues) : null
  const activeDayCount = new Set(items.map((item) => formatDateKey(item.closeTime))).size

  return {
    tradeCount,
    winCount: winValues.length,
    lossCount: lossValues.length,
    winRate: tradeCount ? winValues.length / tradeCount : 0,
    totalPnl,
    totalFee,
    avgPnl: tradeCount ? totalPnl / tradeCount : 0,
    avgWin,
    avgLoss,
    profitLossRatio: avgWin !== null && avgLoss !== null && avgLoss !== 0 ? avgWin / Math.abs(avgLoss) : null,
    maxWin: winValues.length ? Math.max(...winValues) : null,
    maxLoss: lossValues.length ? Math.min(...lossValues) : null,
    activeDayCount,
    avgTradesPerDay: activeDayCount ? tradeCount / activeDayCount : 0,
    maxConsecutiveLosses: calculateMaxConsecutiveLosses(items),
  }
}

function average(values: number[]) {
  return values.reduce((sum, item) => sum + item, 0) / values.length
}

function calculateMaxConsecutiveLosses(items: AnalysisRecord[]) {
  const sortedItems = [...items].sort((a, b) => a.closeTime.getTime() - b.closeTime.getTime())
  let current = 0
  let max = 0
  for (const item of sortedItems) {
    if (item.realPnl < 0) {
      current += 1
      max = Math.max(max, current)
    } else {
      current = 0
    }
  }
  return max
}

function buildPeriodRows(items: AnalysisRecord[], periodType: PeriodType): PeriodRow[] {
  const groups = groupBy(items, (item) => getPeriodInfo(item.closeTime, periodType).key)
  return [...groups.entries()]
    .map(([periodKey, groupItems]) => ({
      periodKey,
      periodLabel: getPeriodInfo(groupItems[0].closeTime, periodType).label,
      ...calculateMetrics(groupItems),
    }))
    .sort((a, b) => a.periodKey.localeCompare(b.periodKey))
}

function buildFactorRows(items: AnalysisRecord[], column: TradeRecordColumn | null): FactorRow[] {
  if (!column) {
    return []
  }

  const groups = new Map<string, AnalysisRecord[]>()
  for (const item of items) {
    const values = getFactorValues(item.record.data_json[column.column_key], column)
    for (const value of values) {
      groups.set(value, [...(groups.get(value) ?? []), item])
    }
  }

  return [...groups.entries()]
    .map(([value, groupItems]) => ({
      factorKey: column.column_key,
      factorLabel: column.column_label,
      factorValue: value,
      factorValueLabel: getFactorValueLabel(column, value),
      sampleWarning: groupItems.length < 3,
      ...calculateMetrics(groupItems),
    }))
    .sort((a, b) => b.totalPnl - a.totalPnl)
}

function getFactorValues(value: unknown, column: TradeRecordColumn) {
  if (column.data_type === "bool") {
    return [value ? "true" : "false"]
  }

  if (column.data_type === "multi_select") {
    return Array.isArray(value) && value.length ? value.map((item) => String(item)) : ["__empty__"]
  }

  return isBlank(value) ? ["__empty__"] : [String(value)]
}

function getFactorValueLabel(column: TradeRecordColumn, value: string) {
  if (value === "__empty__") {
    return "空值"
  }

  if (column.data_type === "bool") {
    return value === "true" ? "是" : "否"
  }

  const option = getColumnOptions(column).find((item) => item.value === value)
  return option?.label ?? value
}

function getColumnOptions(column: TradeRecordColumn): TradeRecordColumnOption[] {
  return (column.options_json ?? []) as TradeRecordColumnOption[]
}

onMounted(loadData)
</script>

<template>
  <section class="trade-record-analysis-page">
    <div class="analysis-card">
      <header class="toolbar">
        <div class="toolbar-left">
          <div class="toolbar-title">
            交易记录分析
            <el-icon class="icon" @click="props.handleModeChange('manager')">
              <Switch />
            </el-icon>
          </div>
          <div class="toolbar-subtitle">按账户、平仓时间和动态因子统计已平仓交易</div>
        </div>
        <div class="toolbar-right">
          <el-select v-model="selectedAccountId" class="account-select" :disabled="!accountColumn" filterable>
            <el-option
              v-for="option in accountOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
          <el-button @click="loadData">刷新</el-button>
          <div class="summary">{{ selectedRecords.length }} / {{ closedAnalysisRecords.length }} 笔已平仓</div>
        </div>
      </header>

      <el-alert
        v-if="missingMessages.length"
        type="warning"
        show-icon
        :closable="false"
        :title="missingMessages.join('、')"
      />

      <template v-if="analysisReady">
        <section v-loading="loading" class="metric-grid">
          <div class="metric-card metric-card-primary">
            <div class="metric-label">真实盈亏</div>
            <div class="metric-value" :class="{ profit: overviewMetrics.totalPnl > 0, loss: overviewMetrics.totalPnl < 0 }">
              {{ formatMoney(overviewMetrics.totalPnl) }}
            </div>
          </div>
          <div class="metric-card metric-card-primary">
            <div class="metric-label">胜率</div>
            <div class="metric-value">{{ formatRate(overviewMetrics.winRate) }}</div>
          </div>
          <div class="metric-card metric-card-primary">
            <div class="metric-label">交易次数</div>
            <div class="metric-value">{{ overviewMetrics.tradeCount }}</div>
          </div>
          <div class="metric-card metric-card-primary">
            <div class="metric-label">盈亏比</div>
            <div class="metric-value">{{ formatRatio(overviewMetrics.profitLossRatio) }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">平均盈利</div>
            <div class="metric-value profit">{{ formatMoney(overviewMetrics.avgWin) }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">平均亏损</div>
            <div class="metric-value loss">{{ formatMoney(overviewMetrics.avgLoss) }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">手续费</div>
            <div class="metric-value">{{ formatMoney(overviewMetrics.totalFee) }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">最长连续亏损</div>
            <div class="metric-value">{{ overviewMetrics.maxConsecutiveLosses }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">日均频率</div>
            <div class="metric-value">{{ overviewMetrics.avgTradesPerDay.toFixed(1) }}</div>
          </div>
        </section>

        <section v-if="selectedAccountId === 'all'" class="analysis-section">
          <div class="section-header">
            <div>
              <div class="section-title">账户对比</div>
              <div class="section-subtitle">全部账户模式下，先看每个账户自己的表现</div>
            </div>
          </div>
          <el-table :data="accountRows" border stripe>
            <el-table-column prop="accountName" label="账户" min-width="150" />
            <el-table-column prop="accountType" label="类型" width="90" />
            <el-table-column prop="tradeCount" label="次数" width="80" />
            <el-table-column label="胜率" width="100">
              <template #default="{ row }">{{ formatRate(row.winRate) }}</template>
            </el-table-column>
            <el-table-column label="真实盈亏" width="120">
              <template #default="{ row }">
                <span :class="{ profit: row.totalPnl > 0, loss: row.totalPnl < 0 }">{{ formatMoney(row.totalPnl) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="平均盈亏" width="120">
              <template #default="{ row }">{{ formatMoney(row.avgPnl) }}</template>
            </el-table-column>
            <el-table-column label="盈亏比" width="100">
              <template #default="{ row }">{{ formatRatio(row.profitLossRatio) }}</template>
            </el-table-column>
            <el-table-column label="最大亏损" width="120">
              <template #default="{ row }">{{ formatMoney(row.maxLoss) }}</template>
            </el-table-column>
            <el-table-column prop="maxConsecutiveLosses" label="连续亏损" width="100" />
          </el-table>
        </section>

        <section class="analysis-section">
          <div class="section-header">
            <div>
              <div class="section-title">周期表现</div>
              <div class="section-subtitle">{{ selectedAccountLabel }}，按平仓时间统计</div>
            </div>
            <el-segmented
              v-model="selectedPeriodType"
              :options="[
                { label: '每日', value: 'day' },
                { label: '每周', value: 'week' },
                { label: '半月', value: 'half_month' },
                { label: '每月', value: 'month' },
              ]"
            />
          </div>
          <el-table :data="periodRows" border stripe height="320">
            <el-table-column prop="periodLabel" label="周期" min-width="140" fixed="left" />
            <el-table-column prop="tradeCount" label="次数" width="80" />
            <el-table-column label="胜率" width="100">
              <template #default="{ row }">{{ formatRate(row.winRate) }}</template>
            </el-table-column>
            <el-table-column label="真实盈亏" width="120">
              <template #default="{ row }">
                <span :class="{ profit: row.totalPnl > 0, loss: row.totalPnl < 0 }">{{ formatMoney(row.totalPnl) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="平均盈亏" width="120">
              <template #default="{ row }">{{ formatMoney(row.avgPnl) }}</template>
            </el-table-column>
            <el-table-column label="平均盈利" width="120">
              <template #default="{ row }">{{ formatMoney(row.avgWin) }}</template>
            </el-table-column>
            <el-table-column label="平均亏损" width="120">
              <template #default="{ row }">{{ formatMoney(row.avgLoss) }}</template>
            </el-table-column>
            <el-table-column label="盈亏比" width="100">
              <template #default="{ row }">{{ formatRatio(row.profitLossRatio) }}</template>
            </el-table-column>
            <el-table-column label="手续费" width="100">
              <template #default="{ row }">{{ formatMoney(row.totalFee) }}</template>
            </el-table-column>
            <el-table-column prop="maxConsecutiveLosses" label="连续亏损" width="100" />
          </el-table>
        </section>

        <section class="analysis-section">
          <div class="section-header">
            <div>
              <div class="section-title">因子相关性</div>
              <div class="section-subtitle">只分析 single_select、multi_select、bool，样本少于 3 笔会标记</div>
            </div>
            <el-select v-model="selectedFactorKey" class="factor-select" placeholder="选择因子字段">
              <el-option
                v-for="column in factorColumns"
                :key="column.column_id"
                :label="column.column_label"
                :value="column.column_key"
              />
            </el-select>
          </div>
          <el-empty v-if="!factorColumns.length" description="暂无可分析因子" />
          <el-table v-else :data="factorRows" border stripe height="360">
            <el-table-column prop="factorValueLabel" label="因子值" min-width="180" fixed="left">
              <template #default="{ row }">
                <span>{{ row.factorValueLabel }}</span>
                <el-tag v-if="row.sampleWarning" class="sample-tag" size="small" type="warning">样本少</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="tradeCount" label="样本数" width="90" />
            <el-table-column label="胜率" width="100">
              <template #default="{ row }">{{ formatRate(row.winRate) }}</template>
            </el-table-column>
            <el-table-column label="真实盈亏" width="120">
              <template #default="{ row }">
                <span :class="{ profit: row.totalPnl > 0, loss: row.totalPnl < 0 }">{{ formatMoney(row.totalPnl) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="平均盈亏" width="120">
              <template #default="{ row }">{{ formatMoney(row.avgPnl) }}</template>
            </el-table-column>
            <el-table-column label="平均盈利" width="120">
              <template #default="{ row }">{{ formatMoney(row.avgWin) }}</template>
            </el-table-column>
            <el-table-column label="平均亏损" width="120">
              <template #default="{ row }">{{ formatMoney(row.avgLoss) }}</template>
            </el-table-column>
            <el-table-column label="盈亏比" width="100">
              <template #default="{ row }">{{ formatRatio(row.profitLossRatio) }}</template>
            </el-table-column>
            <el-table-column label="最大盈利" width="120">
              <template #default="{ row }">{{ formatMoney(row.maxWin) }}</template>
            </el-table-column>
            <el-table-column label="最大亏损" width="120">
              <template #default="{ row }">{{ formatMoney(row.maxLoss) }}</template>
            </el-table-column>
          </el-table>
        </section>
      </template>
    </div>
  </section>
</template>

<style scoped lang="less">
.trade-record-analysis-page {
  padding: 16px;
}

.analysis-card {
  display: flex;
  flex-direction: column;
  row-gap: 14px;
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
  display: flex;
  align-items: center;
  column-gap: 4px;
  color: #1a2233;
  font-size: 20px;
  font-weight: 700;
}

.icon {
  cursor: pointer;

  &:hover {
    color: #409eff;
  }
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
  gap: 10px;
}

.account-select {
  width: 240px;
}

.factor-select {
  width: 260px;
}

.summary {
  color: #5f6b7c;
  font-size: 13px;
  white-space: nowrap;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  position: relative;
  grid-column: span 2;
  min-height: 86px;
  padding: 14px 16px;
  overflow: hidden;
  border: 1px solid #e4e8f0;
  border-radius: 8px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.96)),
    #fff;
  box-shadow: 0 8px 20px rgba(31, 42, 61, 0.05);
}

.metric-card::before {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 3px;
  content: "";
  background: #d8dee9;
}

.metric-card-primary {
  grid-column: span 3;
  min-height: 104px;
  padding: 16px 18px;
  background:
    linear-gradient(135deg, rgba(239, 246, 255, 0.95), rgba(255, 255, 255, 0.98) 48%, rgba(240, 253, 244, 0.88)),
    #fff;
}

.metric-card-primary::before {
  background: linear-gradient(90deg, #2563eb, #10b981);
}

.metric-label {
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.metric-value {
  margin-top: 8px;
  color: #1f2a3d;
  font-size: 22px;
  font-weight: 700;
  line-height: 1.15;
}

.metric-card-primary .metric-value {
  font-size: 28px;
}

.analysis-section {
  padding-top: 4px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.section-title {
  color: #1f2a3d;
  font-size: 16px;
  font-weight: 700;
}

.section-subtitle {
  margin-top: 3px;
  color: #7d8899;
  font-size: 12px;
}

.profit {
  color: #0f9f6e;
}

.loss {
  color: #d93025;
}

.sample-tag {
  margin-left: 8px;
}

@media (max-width: 1200px) {
  .metric-grid {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }

  .metric-card,
  .metric-card-primary {
    grid-column: span 2;
  }
}

@media (max-width: 900px) {
  .toolbar,
  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .toolbar-right,
  .account-select,
  .factor-select {
    width: 100%;
  }

  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metric-card,
  .metric-card-primary {
    grid-column: span 1;
    min-height: 92px;
  }

  .metric-card-primary .metric-value {
    font-size: 24px;
  }
}
</style>
