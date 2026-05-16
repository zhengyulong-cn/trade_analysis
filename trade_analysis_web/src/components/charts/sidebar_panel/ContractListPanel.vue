<script setup lang="ts">
import {
  getFutureOpportunityAnalysisItemApi,
  type FutureOpportunityAnalysisItem,
} from '@/api/modules'
import { Star, StarFilled } from '@element-plus/icons-vue'
import {
  formatOpportunityAction,
  formatOpportunityDirection,
  formatOpportunityMode,
  formatOpportunityMomentumState,
  formatOpportunityNumber,
  formatOpportunityOpenSide,
  formatOpportunitySegmentType,
  formatOpportunityTradingRangeState,
  opportunityModeTagType,
  OPPORTUNITY_UNKNOWN_TEXT,
} from '@/utils/opportunity'
import { ref, watch } from 'vue'

interface ContractOption {
  label: string
  value: string
  description?: string
  isFavorite?: boolean
}

const props = withDefaults(
  defineProps<{
    contractOptions?: ContractOption[]
    selectedContract?: string
  }>(),
  {
    contractOptions: () => [],
    selectedContract: '',
  },
)

const emit = defineEmits<{
  close: []
  select: [value: string]
  toggleFavorite: [value: string]
}>()

const opportunityLoading = ref(false)
const opportunityItem = ref<FutureOpportunityAnalysisItem | null>(null)

const loadOpportunity = async (symbol: string) => {
  if (!symbol) {
    opportunityItem.value = null
    return
  }

  opportunityLoading.value = true
  try {
    opportunityItem.value = await getFutureOpportunityAnalysisItemApi({ symbol })
  } catch {
    opportunityItem.value = null
  } finally {
    opportunityLoading.value = false
  }
}

watch(
  () => props.selectedContract,
  (value) => {
    void loadOpportunity(value)
  },
  { immediate: true },
)

const handleContractSelect = (contractValue: string) => {
  emit('select', contractValue)
}

const handleToggleFavorite = (contractValue: string) => {
  emit('toggleFavorite', contractValue)
}
</script>

<template>
  <div class="contract-panel">
    <div class="contract-list">
      <button
        v-for="contract in contractOptions"
        :key="contract.value"
        type="button"
        class="contract-item"
        :class="{ 'is-active': contract.value === selectedContract }"
        @click="handleContractSelect(contract.value)"
      >
        <div class="contract-item__header">
          <div class="contract-code">{{ contract.label }}</div>
          <button
            type="button"
            class="favorite-button"
            :class="{ 'favorite-button--active': contract.isFavorite }"
            @click.stop="handleToggleFavorite(contract.value)"
          >
            <el-icon>
              <StarFilled v-if="contract.isFavorite" />
              <Star v-else />
            </el-icon>
          </button>
        </div>
        <div>{{ contract.value }}</div>
      </button>
    </div>
    <div v-loading="opportunityLoading" class="opportunity-box">
      <template v-if="opportunityItem">
        <div class="opportunity-grid">
          <div class="info-item info-item--full info-item--momentum">
            <span class="info-label">机会判断</span>
            <span class="info-value info-value--primary">{{ formatOpportunityAction(opportunityItem) }}</span>
          </div>

          <div class="info-item">
            <span class="info-label">最新价</span>
            <span class="info-value">{{ formatOpportunityNumber(opportunityItem.latest_price) }}</span>
          </div>

          <div class="info-item">
            <span class="info-label">模式</span>
            <span class="info-value">
              <el-tag v-if="opportunityItem.opportunity_mode" :type="opportunityModeTagType(opportunityItem.opportunity_mode)">
                {{ formatOpportunityMode(opportunityItem.opportunity_mode) }}
              </el-tag>
              <span v-else>{{ OPPORTUNITY_UNKNOWN_TEXT }}</span>
            </span>
          </div>

          <div class="info-item">
            <span class="info-label">4H方向</span>
            <span class="info-value">{{ formatOpportunityDirection(opportunityItem.current_4h_segment_direction) }}</span>
          </div>

          <div class="info-item">
            <span class="info-label">30F方向</span>
            <span class="info-value">{{ formatOpportunityDirection(opportunityItem.current_30f_segment_direction) }}</span>
          </div>

          <div class="info-item">
            <span class="info-label">30F类型</span>
            <span class="info-value">{{ formatOpportunitySegmentType(opportunityItem.current_30f_segment_type) }}</span>
          </div>

          <div class="info-item">
            <span class="info-label">操作视角</span>
            <span class="info-value">{{ formatOpportunityOpenSide(opportunityItem.open_side) }}</span>
          </div>

          <div class="info-item info-item--full info-item--momentum">
            <span class="info-label">30F交易区间</span>
            <span class="info-value">{{ formatOpportunityTradingRangeState(opportunityItem) }}</span>
          </div>

          <div class="info-item info-item--full">
            <span class="info-label">30F动能</span>
            <span
              class="info-value"
              :class="{ 'info-value--exhausted': opportunityItem.current_30f_momentum_exhausted }"
            >
              {{
                formatOpportunityMomentumState(
                  opportunityItem.current_30f_momentum_check_direction,
                  opportunityItem.current_30f_momentum_exhausted,
                )
              }}
            </span>
          </div>

          <div class="info-item info-item--full">
            <span class="info-label">5F动能</span>
            <span
              class="info-value"
              :class="{ 'info-value--exhausted': opportunityItem.current_5f_momentum_exhausted }"
            >
              {{
                formatOpportunityMomentumState(
                  opportunityItem.current_5f_momentum_check_direction,
                  opportunityItem.current_5f_momentum_exhausted,
                )
              }}
            </span>
          </div>
        </div>
      </template>

      <div v-else class="placeholder-content">
        暂无合约分析结果
      </div>
    </div>
  </div>
</template>

<style lang="less" scoped>
.contract-panel {
  width: 100%;
  height: 100%;

  :deep(.el-collapse) {
    border: none;
    --el-collapse-header-height: 36px;
  }

  :deep(.el-collapse-item__header) {
    font-size: 13px;
    font-weight: 500;
    color: #475569;
    border: none;
    padding: 0 4px;
    border-radius: 8px;

    &:hover {
      background: #f1f5f9;
    }
  }

  :deep(.el-collapse-item__wrap) {
    border: none;
  }

  :deep(.el-collapse-item__content) {
    padding: 4px 0 8px;
  }
}

.contract-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 30rem;
  overflow: auto;
}

.contract-item {
  width: 100%;
  border: none;
  border-radius: 0.5rem;
  background: transparent;
  padding: 0px .5rem;
  text-align: left;
  color: #0f172a;
  cursor: pointer;
  display: flex;
  flex-direction:  column;
  align-items: flex-start;
  gap: 2px;
  transition: background-color 0.15s ease;
}

.contract-item__header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.contract-item:hover {
  background: #f1f5f9;
}

.contract-item.is-active {
  background: #f1f5f9;
  color: #0f172a;
}

.contract-code {
  font-size: 1rem;
  font-weight: 600;
}

.favorite-button {
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #c0c4cc;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition:
    color 0.2s ease,
    background-color 0.2s ease;
}

.favorite-button:hover {
  color: #e6a23c;
  background: rgba(230, 162, 60, 0.1);
}

.favorite-button--active {
  color: #e6a23c;
}

.opportunity-box {
  max-height: 18rem;
  margin-top: .5rem;
  overflow: auto;
}

.opportunity-title {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 10px;
  color: #0f172a;
}

.opportunity-title span {
  font-size: 12px;
  color: #64748b;
}

.opportunity-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #f8fafc;
}

.info-item--full {
  grid-column: 1 / -1;
}

.info-item--momentum {
  border: 1px solid #e2e8f0;
}

.info-label {
  font-size: 12px;
  color: #94a3b8;
}

.info-value {
  font-size: 12px;
  color: #0f172a;
  line-height: 1.4;
  word-break: break-word;
}

.info-value--primary {
  font-weight: 600;
}

.opportunity-grid .info-value--exhausted {
  color: #dc2626;
  font-weight: 600;
}

.placeholder-content {
  min-height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  font-size: 13px;
}
</style>
