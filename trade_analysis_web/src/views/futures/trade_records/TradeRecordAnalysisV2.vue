<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { getTradeAccountListApi, getTradeRecordColumnListApi, getTradeRecordListApi, type TradeAccount, type TradeRecord, type TradeRecordColumn } from '@/api/modules';
import { ElMessage } from 'element-plus';

const selectedAccountId = ref("")
const accounts = ref<TradeAccount[]>([])
const sourceRecords = ref<TradeRecord[]>([])
const columns = ref<TradeRecordColumn[]>([])

const loading = ref<boolean>(false)

const props = defineProps<{
  handleModeChange: (mode: string | number | boolean) => void
}>()

interface AnalysisRecord {
  accountId: string
  openTime: Date
  closeTime: Date
  tradeDay: Date
  operatePnl: number
  fee: number
  realPnl: number
}

interface Metrics {
  tradeCount: number
  winCount: number
  lossCount: number
  winRate: number
  opTotalPnl: number
  realTotalPnl: number
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
    sourceRecords.value = recordList

    selectedAccountId.value = String(accountList[0]!.account_id)
  } catch {
    ElMessage.error("交易记录分析数据加载失败")
  } finally {
    loading.value = false
  }
}

const accountOptions = computed(() => [
  ...accounts.value.map((account) => ({
    label: `${account.account_name}（${account.account_type === "real" ? "实盘" : "模拟"}）`,
    value: String(account.account_id),
  })),
])

const enabledColumns = computed(() => columns.value.filter((item) => item.is_enabled))

const findColumn = (keys: string[], labels: string[]) => {
  const normalizedKeys = new Set(keys.map((item) => item.toLowerCase()))
  return (
    enabledColumns.value.find((column) => normalizedKeys.has(column.column_key.toLowerCase())) ??
    enabledColumns.value.find((column) => labels.some((label) => column.column_label.includes(label))) ??
    null
  )
}

const accountColumn = computed(() =>
  enabledColumns.value.find(
    (column) =>
      column.data_type === "single_select" &&
      String(column.option_source_config?.source ?? "") === "trade_accounts",
  ),
)

const operatePnlColumn = computed(() => findColumn(["operate_pnl", "operation_pnl"], ["操作盈亏"]))
const feeColumn = computed(() => findColumn(["fee"], ["手续费"]))
const openTimeColumn = computed(() => findColumn(["open_time"], ["开仓时间"]))
const closeTimeColumn = computed(() => findColumn(["close_time"], ["平仓时间"]))
const closePriceColumn = computed(() => findColumn(["close_price"], ["平仓价格"]))

const isBlank = (value: unknown) => {
  return value === null || value === undefined || (typeof value === "string" && !value.trim())
}

const toNumber = (value: unknown) => {
  if (isBlank(value)) {
    return null
  }
  const numericValue = Number(value)
  return Number.isFinite(numericValue) ? numericValue : null
}

const parseDate = (value: unknown) => {
  if (value instanceof Date && Number.isFinite(value.getTime())) {
    return value
  }
  const date = new Date(String(value))
  return Number.isFinite(date.getTime()) ? date : null
}

const groupBy = <T>(items: T[], getKey: (item: T) => string) => {
  const groups = new Map<string, T[]>()
  for (const item of items) {
    const key = getKey(item)
    groups.set(key, [...(groups.get(key) ?? []), item])
  }
  return groups
}

/**
 * 根据真实时间计算交易日
 *
 * 交易日规则：
 * 周五21:00 ~ 周一15:00 => 周一交易日
 * 周一21:00 ~ 周二15:00 => 周二交易日
 * 周二21:00 ~ 周三15:00 => 周三交易日
 * 周三21:00 ~ 周四15:00 => 周四交易日
 * 周四21:00 ~ 周五15:00 => 周五交易日
 *
 * 返回值为交易日当天 00:00:00
 */
const calcTradeDay = (date: Date): Date => {
  const shDate = new Date(
    date.toLocaleString("zh-CN", { timeZone: "Asia/Shanghai" })
  );
  const tradeDay = new Date(shDate);

  const week = tradeDay.getDay(); // 0=周日 1=周一 ... 5=周五 6=周六
  const minutes = tradeDay.getHours() * 60 + tradeDay.getMinutes();

  // 周六 -> 下周一
  if (week === 6) {
    tradeDay.setDate(tradeDay.getDate() + 2);
  }
  // 周日 -> 下周一
  else if (week === 0) {
    tradeDay.setDate(tradeDay.getDate() + 1);
  }
  // 夜盘（21:00及以后）
  else if (minutes >= 21 * 60) {
    if (week === 5) {
      // 周五夜盘 -> 下周一
      tradeDay.setDate(tradeDay.getDate() + 3);
    } else {
      // 周一~周四夜盘 -> 下一天
      tradeDay.setDate(tradeDay.getDate() + 1);
    }
  }

  tradeDay.setHours(0, 0, 0, 0);
  return tradeDay;
}

const formatRecords = computed<AnalysisRecord[]>(() => {
  return sourceRecords.value
    .map((record) => {
      const closeTimeValue = record.data_json[closeTimeColumn.value!.column_key]
      const closePriceValue = record.data_json[closePriceColumn.value!.column_key]
      if (isBlank(closeTimeValue) || isBlank(closePriceValue)) {
        return null
      }
      const closeTime = parseDate(closeTimeValue)
      const openTime = parseDate(record.data_json[openTimeColumn.value!.column_key])
      const operatePnl = toNumber(record.data_json[operatePnlColumn.value!.column_key])
      if (!closeTime || !openTime || operatePnl === null) {
        return null
      }
      const fee = toNumber(record.data_json[feeColumn.value!.column_key]) ?? 0
      const rawAccountId = record.data_json[accountColumn.value!.column_key]
      const accountId = String(rawAccountId)

      const tradeDay = calcTradeDay(openTime)
      return {
        // record,
        accountId,
        openTime,
        closeTime,
        tradeDay,
        operatePnl,
        fee,
        realPnl: operatePnl - fee,
      } satisfies AnalysisRecord
    })
    .filter((item): item is AnalysisRecord => Boolean(item))
})

const selectedRecords = computed(() => {
  return formatRecords.value.filter((item) => item.accountId === selectedAccountId.value)
})

const analysisReady = computed(
  () =>
    Boolean(accountColumn.value) &&
    Boolean(operatePnlColumn.value) &&
    Boolean(feeColumn.value) &&
    Boolean(openTimeColumn.value) &&
    Boolean(closeTimeColumn.value) &&
    Boolean(closePriceColumn.value),
)

const calculateMaxConsecutiveLosses = (items: AnalysisRecord[]) => {
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

const formatMoney = (value: number | null) => {
  if (value === null || !Number.isFinite(value)) {
    return "-"
  }
  return value.toFixed(2)
}

const formatRate = (value: number) => {
  if (!Number.isFinite(value)) {
    return "-"
  }
  return `${(value * 100).toFixed(1)}%`
}

const formatRatio = (value: number | null) => {
  if (value === null || !Number.isFinite(value)) {
    return "-"
  }
  return value.toFixed(2)
}

const formatDateKey = (date: Date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

const average = (values: number[]) => {
  return values.reduce((sum, item) => sum + item, 0) / values.length
}

function calculateMetrics(items: AnalysisRecord[]): Metrics {
  const tradeCount = items.length
  const opPnlValues = items.map((item) => item.operatePnl)
  const realPnlValues = items.map((item) => item.realPnl)
  const winValues = realPnlValues.filter((item) => item > 0)
  const lossValues = realPnlValues.filter((item) => item < 0)
  const opTotalPnl = opPnlValues.reduce((sum, item) => sum + item, 0)
  const realTotalPnl = realPnlValues.reduce((sum, item) => sum + item, 0)
  const totalFee = items.reduce((sum, item) => sum + item.fee, 0)
  const avgWin = winValues.length ? average(winValues) : null
  const avgLoss = lossValues.length ? average(lossValues) : null
  const activeDayCount = new Set(items.map((item) => formatDateKey(item.closeTime))).size

  return {
    tradeCount,
    winCount: winValues.length,
    lossCount: lossValues.length,
    winRate: tradeCount ? winValues.length / tradeCount : 0,
    realTotalPnl,
    opTotalPnl,
    totalFee,
    avgPnl: tradeCount ? realTotalPnl / tradeCount : 0,
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

const overviewMetrics = computed(() => calculateMetrics(selectedRecords.value))

const buildPeriodRows = (analysisRecords: AnalysisRecord[]) => {
  const groups = groupBy(analysisRecords, (item) => formatDateKey(item.tradeDay))
  return [...groups.entries()].sort(([a], [b]) => b.localeCompare(a)).map(([tradeDayKey, groupItems]) => ({
    tradeDayKey,
    ...calculateMetrics(groupItems)
  }))
}

const periodRows = computed(() => buildPeriodRows(selectedRecords.value))



onMounted(loadData)
</script>

<template>
  <section class="analysis-page">
    <header class="toolbar">
      <div class="toolbar-left">
        <div class="toolbar-title">
          交易记录分析
          <el-icon class="icon" @click="props.handleModeChange('manager')">
            <Switch />
          </el-icon>
        </div>
      </div>
      <div class="toolbar-right">
        <el-select v-model="selectedAccountId" class="account-select" filterable>
          <el-option
            v-for="option in accountOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <el-button @click="loadData">刷新</el-button>
        <div class="summary">
          {{ selectedRecords.length }} 笔交易数据
        </div>
      </div>
    </header>
    <section v-if="analysisReady" v-loading="loading" class="metric-grid">
      <div class="metric-card metric-card-primary">
        <div class="metric-label">真实盈亏</div>
        <div class="metric-value" :class="{ profit: overviewMetrics.realTotalPnl > 0, loss: overviewMetrics.realTotalPnl < 0 }">
          {{ formatMoney(overviewMetrics.realTotalPnl) }}
        </div>
      </div>
      <div class="metric-card">
        <div class="metric-label">手续费</div>
        <div class="metric-value">{{ formatMoney(overviewMetrics.totalFee) }}</div>
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
    </section>
    <section class="trade-day-analysis-table">
      <el-table :data="periodRows" border stripe height="420">
        <el-table-column prop="tradeDayKey" label="交易日" width="120" fixed="left" />
        <el-table-column prop="tradeCount" label="交易次数" min-width="100" />
        <el-table-column label="胜率" min-width="100">
          <template #default="{ row }">{{ formatRate(row.winRate) }}</template>
        </el-table-column>
        <el-table-column label="手续费" min-width="100">
          <template #default="{ row }">
            <span class="loss">{{ formatMoney(row.totalFee) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作盈亏" min-width="120">
          <template #default="{ row }">
            <span :class="{ profit: row.opTotalPnl > 0, loss: row.opTotalPnl < 0 }">{{ formatMoney(row.opTotalPnl) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="真实盈亏" min-width="120">
          <template #default="{ row }">
            <span :class="{ profit: row.realTotalPnl > 0, loss: row.realTotalPnl < 0 }">{{ formatMoney(row.realTotalPnl) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="平均盈利" min-width="120">
          <template #default="{ row }">{{ formatMoney(row.avgWin) }}</template>
        </el-table-column>
        <el-table-column label="平均亏损" min-width="120">
          <template #default="{ row }">{{ formatMoney(row.avgLoss) }}</template>
        </el-table-column>
        <el-table-column label="盈亏比" min-width="100">
          <template #default="{ row }">{{ formatRatio(row.profitLossRatio) }}</template>
        </el-table-column>
        <el-table-column prop="maxConsecutiveLosses" label="连续亏损" width="100" />
      </el-table>
    </section>
  </section>
</template>

<style lang="less">
.analysis-page {
  padding: 16px;
  display: flex;
  flex-direction: column;
  row-gap: .75rem;
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

.toolbar-right {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 10px;
}

.account-select {
  width: 240px;
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

  .metric-card {
    position: relative;
    grid-column: span 1;
    padding: 14px 16px;
    overflow: hidden;
    border: 1px solid #e4e8f0;
    border-radius: 8px;
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.96)),
      #fff;
    box-shadow: 0 8px 20px rgba(31, 42, 61, 0.05);
    .profit {
      color: #0f9f6e;
    }
    
    .loss {
      color: #d93025;
    }
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
    grid-column: span 2;
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
}

.trade-day-analysis-table {
  .profit {
    color: #0f9f6e;
  }
  
  .loss {
    color: #d93025;
  }
}
</style>