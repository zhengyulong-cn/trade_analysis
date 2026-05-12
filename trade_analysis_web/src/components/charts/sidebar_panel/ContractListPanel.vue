<script setup lang="ts">
import {
  getFutureOpportunityAnalysisItemApi,
  type FutureOpportunityAnalysisItem,
} from '@/api/modules'
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
import { computed, ref, watch } from 'vue'

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
}>()

const activeNames = ref<string[]>(['contracts', 'opportunity'])
const opportunityLoading = ref(false)
const opportunityItem = ref<FutureOpportunityAnalysisItem | null>(null)

const selectedContractLabel = computed(() => {
  const matched = props.contractOptions.find((item) => item.value === props.selectedContract)
  return matched?.description || matched?.label || props.selectedContract || OPPORTUNITY_UNKNOWN_TEXT
})

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
</script>

<template>
  <div class="contract-panel">
    <el-collapse v-model="activeNames">
      <el-collapse-item title="合约列表" name="contracts">
        <div class="contract-list">
          <button
            v-for="contract in contractOptions"
            :key="contract.value"
            type="button"
            class="contract-item"
            :class="{ 'is-active': contract.value === selectedContract }"
            @click="handleContractSelect(contract.value)"
          >
            <div class="contract-code">{{ contract.value }}</div>
          </button>
        </div>
      </el-collapse-item>

      <el-collapse-item title="合约情况" name="opportunity">
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
      </el-collapse-item>
    </el-collapse>
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
  border-radius: 8px;
  background: transparent;
  padding: 8px 10px;
  text-align: left;
  color: #0f172a;
  cursor: pointer;
  display: flex;
  flex-direction:  row;
  align-items: center;
  gap: 2px;
  transition: background-color 0.15s ease;
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

.opportunity-box {
  height: 12rem;
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
