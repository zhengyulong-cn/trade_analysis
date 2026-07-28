<script setup lang="ts">
import type { FutureContract } from '@/api/modules'
import { computed } from 'vue';
import { storeToRefs } from 'pinia'
import { useRealtimeMarketStore } from '@/stores/realtimeMarket'
const props = withDefaults(
  defineProps<{
    contracts?: FutureContract[]
    selectedContract?: string
  }>(),
  {
    contracts: () => [],
    selectedContract: '',
  },
)
const emit = defineEmits<{
  'update:selectedContract': [value: string]
  'toggleFavorite': [value: string]
}>()
const realtimeMarketStore = useRealtimeMarketStore()
const { quotes } = storeToRefs(realtimeMarketStore)
const selectedContractId = computed(() => {
  return props.contracts.find((item) => item.symbol === props.selectedContract)?.contract_id
})

const handleContractSelect = (contractValue: string) => {
  if (contractValue && contractValue !== props.selectedContract) {
    emit('update:selectedContract', contractValue)
  }
}

const getLatestPrice = (symbol: string) => {
  const price = Number(quotes.value[symbol]?.last_price)
  return Number.isFinite(price) ? price.toLocaleString('zh-CN', { maximumFractionDigits: 4 }) : '--'
}
</script>

<template>
  <section class="contracts-panel">
    <div class="panel-header">
      <span>合约列表</span>
      <strong>{{ contracts.length }}</strong>
    </div>
    <el-scrollbar class="contract-scrollbar" height="45rem">
      <button
        v-for="contract in contracts"
        :key="contract.contract_id"
        type="button"
        class="contract-item"
        :class="{ 'is-selected': contract.contract_id === selectedContractId }"
        @click="handleContractSelect(contract.symbol)"
      >
        <span class="contract-symbol">{{ contract.symbol }}</span>
        <span class="contract-price">{{ getLatestPrice(contract.symbol) }}</span>
        <span class="contract-name">{{ contract.name }}</span>
      </button>
    </el-scrollbar>
  </section>
</template>

<style scoped lang="less">
.contracts-panel {
  height: 100%;
  width: 10rem;
  display: flex;
  flex-direction: column;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.panel-header {
  height: 40px;
  flex: 0 0 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  border-bottom: 1px solid #e2e8f0;
  color: #0f172a;
  font-size: 13px;
  font-weight: 600;
}

.panel-header strong {
  color: #64748b;
  font-size: 12px;
}

.contract-scrollbar {
  flex: 1;
}

.contract-item {
  width: 100%;
  min-height: 58px;
  padding: 9px 12px;
  border: none;
  border-bottom: 1px solid #f1f5f9;
  background: transparent;
  color: #334155;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  column-gap: 8px;
  row-gap: 4px;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.contract-item:hover {
  background: #f8fafc;
}

.contract-item.is-selected {
  background: #eff6ff;
  color: #1d4ed8;
}

.contract-symbol {
  min-width: 0;
  overflow: hidden;
  font-size: 14px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.contract-name {
  grid-column: 1 / -1;
  min-width: 0;
  overflow: hidden;
  color: #64748b;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.contract-price {
  justify-self: end;
  color: #0f766e;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
</style>
