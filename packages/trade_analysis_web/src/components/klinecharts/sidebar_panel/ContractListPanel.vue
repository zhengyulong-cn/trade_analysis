<script setup lang="ts">
import { Delete, Plus } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import type { FutureContract, Watchlist, WatchlistContract } from '@/api/modules'
import { useRealtimeMarketStore } from '@/stores/realtimeMarket'

const props = withDefaults(defineProps<{
  watchlists: Watchlist[]
  activeWatchlistId: number | null
  contracts: WatchlistContract[]
  availableContracts: FutureContract[]
  selectedContract?: string
}>(), {
  selectedContract: '',
})

const emit = defineEmits<{
  'update:selectedContract': [value: string]
  'update:activeWatchlistId': [value: number]
  'create-watchlist': [name: string]
  'delete-watchlist': [watchlistId: number]
  'add-contract': [contractId: number]
  'remove-contract': [contractId: number]
  'reorder-contracts': [contractIds: number[]]
}>()

const realtimeMarketStore = useRealtimeMarketStore()
const { quotes } = storeToRefs(realtimeMarketStore)
const draggingContractId = ref<number | null>(null)
const localContracts = ref<WatchlistContract[]>([])
const contractToAdd = ref<number | null>(null)

watch(() => props.contracts, (contracts) => {
  localContracts.value = [...contracts]
}, { immediate: true })

const selectedContractId = computed(() => {
  return localContracts.value.find((item) => item.symbol === props.selectedContract)?.contract_id
})

const addableContracts = computed(() => {
  const includedIds = new Set(localContracts.value.map((item) => item.contract_id))
  return props.availableContracts.filter((contract) => !includedIds.has(contract.contract_id))
})

const getLatestPrice = (symbol: string) => {
  const price = Number(quotes.value[symbol]?.last_price)
  return Number.isFinite(price) ? price.toLocaleString('zh-CN', { maximumFractionDigits: 4 }) : '--'
}

const selectContract = (symbol: string) => {
  if (symbol !== props.selectedContract) {
    emit('update:selectedContract', symbol)
  }
}

const createWatchlist = async () => {
  try {
    const { value } = await ElMessageBox.prompt('输入自选表名称', '新建自选表', {
      confirmButtonText: '创建',
      cancelButtonText: '取消',
      inputPattern: /\S+/,
      inputErrorMessage: '名称不能为空',
    })
    emit('create-watchlist', value)
  } catch {
    // Cancelled dialogs do not need feedback.
  }
}

const addContract = () => {
  if (contractToAdd.value === null) {
    return
  }
  emit('add-contract', contractToAdd.value)
  contractToAdd.value = null
}

const dragStart = (contractId: number) => {
  draggingContractId.value = contractId
}

const dropContract = (targetContractId: number) => {
  const sourceContractId = draggingContractId.value
  draggingContractId.value = null
  if (sourceContractId === null || sourceContractId === targetContractId) {
    return
  }
  const sourceIndex = localContracts.value.findIndex((item) => item.contract_id === sourceContractId)
  const targetIndex = localContracts.value.findIndex((item) => item.contract_id === targetContractId)
  if (sourceIndex < 0 || targetIndex < 0) {
    return
  }
  const nextContracts = [...localContracts.value]
  const [movedContract] = nextContracts.splice(sourceIndex, 1)
  if (!movedContract) {
    return
  }
  nextContracts.splice(targetIndex, 0, movedContract)
  localContracts.value = nextContracts
  emit('reorder-contracts', nextContracts.map((item) => item.contract_id))
}
</script>

<template>
  <section class="contracts-panel">
    <div class="watchlist-tabs">
      <el-tabs
        :model-value="activeWatchlistId === null ? '' : String(activeWatchlistId)"
        type="card"
        @update:model-value="emit('update:activeWatchlistId', Number($event))"
        @tab-remove="emit('delete-watchlist', Number($event))"
      >
        <el-tab-pane
          v-for="watchlist in watchlists"
          :key="watchlist.watchlist_id"
          :label="`${watchlist.name} (${watchlist.item_count})`"
          :name="String(watchlist.watchlist_id)"
          :closable="watchlists.length > 1"
        />
      </el-tabs>
      <el-button :icon="Plus" circle size="small" @click="createWatchlist" />
    </div>
    <div class="add-contract-row">
      <el-select v-model="contractToAdd" filterable placeholder="添加合约" size="small">
        <el-option
          v-for="contract in addableContracts"
          :key="contract.contract_id"
          :label="`${contract.symbol} ${contract.name}`"
          :value="contract.contract_id"
        />
      </el-select>
      <el-button type="primary" size="small" :disabled="contractToAdd === null" @click="addContract">添加</el-button>
    </div>
    <el-scrollbar class="contract-scrollbar" height="45rem">
      <button
        v-for="contract in localContracts"
        :key="contract.contract_id"
        type="button"
        draggable="true"
        class="contract-item"
        :class="{ 'is-selected': contract.contract_id === selectedContractId }"
        @click="selectContract(contract.symbol)"
        @dragstart="dragStart(contract.contract_id)"
        @dragover.prevent
        @drop="dropContract(contract.contract_id)"
      >
        <span class="drag-handle">⠿</span>
        <span class="contract-symbol">{{ contract.symbol }}</span>
        <span class="contract-price">{{ getLatestPrice(contract.symbol) }}</span>
        <span class="contract-name">{{ contract.name }}</span>
        <el-icon class="remove-contract" @click.stop="emit('remove-contract', contract.contract_id)"><Delete /></el-icon>
      </button>
    </el-scrollbar>
  </section>
</template>

<style scoped lang="less">
.contracts-panel { width: 18rem; height: 100%; display: flex; flex-direction: column; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; }
.watchlist-tabs { display: flex; align-items: center; gap: 6px; padding: 8px 8px 0; }
.watchlist-tabs :deep(.el-tabs) { flex: 1; min-width: 0; }
.watchlist-tabs :deep(.el-tabs__header) { margin: 0; }
.add-contract-row { display: flex; gap: 6px; padding: 8px; border-bottom: 1px solid #e2e8f0; }
.add-contract-row .el-select { flex: 1; }
.contract-scrollbar { flex: 1; }
.contract-item { width: 100%; min-height: 58px; padding: 9px 10px; border: none; border-bottom: 1px solid #f1f5f9; background: transparent; color: #334155; display: grid; grid-template-columns: auto minmax(0, 1fr) auto auto; column-gap: 7px; row-gap: 4px; text-align: left; cursor: pointer; }
.contract-item:hover { background: #f8fafc; }
.contract-item.is-selected { background: #eff6ff; color: #1d4ed8; }
.drag-handle { grid-row: 1 / span 2; align-self: center; color: #94a3b8; cursor: grab; }
.contract-symbol { min-width: 0; overflow: hidden; font-size: 14px; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.contract-price { justify-self: end; color: #0f766e; font-size: 13px; font-variant-numeric: tabular-nums; font-weight: 600; }
.contract-name { grid-column: 2 / 4; min-width: 0; overflow: hidden; color: #64748b; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.remove-contract { grid-column: 4; grid-row: 1 / span 2; align-self: center; color: #94a3b8; opacity: 0; }
.contract-item:hover .remove-contract { opacity: 1; }
</style>
