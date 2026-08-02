<script setup lang="ts">
import { computed, ref } from 'vue'
import type { FutureContract, Watchlist, WatchlistContract } from '@/api/modules'
import { Collection, Monitor } from '@element-plus/icons-vue'
import ContractListPanel from './sidebar_panel/ContractListPanel.vue';
import PositionPanel from './sidebar_panel/PositionPanel.vue'

enum PanelTypeEnum {
  Contracts = 'contracts',
  Monitor = 'Monitor',
}

const props = withDefaults(
  defineProps<{
    contracts?: FutureContract[]
    watchlists?: Watchlist[]
    activeWatchlistId?: number | null
    watchlistContracts?: WatchlistContract[]
    selectedContract?: string
    latestPrice?: number
  }>(),
  {
    contracts: () => [],
    watchlists: () => [],
    activeWatchlistId: null,
    watchlistContracts: () => [],
    selectedContract: '',
    latestPrice: undefined,
  },
)

const emit = defineEmits<{
  'update:selectedContract': [value: string]
  'update:activeWatchlistId': [value: number]
  'create-watchlist': [name: string]
  'delete-watchlist': [watchlistId: number]
  'add-contract': [contractId: number]
  'remove-contract': [contractId: number]
  'reorder-contracts': [contractIds: number[]]
}>()

const activeSidePanel = ref<PanelTypeEnum | null>(null)
const hasContractOptions = computed(() => props.watchlists.length > 0)

const toggleSidePanel = (panel: PanelTypeEnum) => {
  activeSidePanel.value = activeSidePanel.value === panel ? null : panel
}
</script>

<template>
  <div class="chart-sidebar-box">
    <div v-if="activeSidePanel">
      <ContractListPanel
        v-if="activeSidePanel === PanelTypeEnum.Contracts"
        :watchlists="watchlists"
        :active-watchlist-id="activeWatchlistId"
        :contracts="watchlistContracts"
        :available-contracts="contracts"
        :selected-contract="selectedContract"
        :latest-price="latestPrice"
        @update:selected-contract="emit('update:selectedContract', $event)"
        @update:active-watchlist-id="emit('update:activeWatchlistId', $event)"
        @create-watchlist="emit('create-watchlist', $event)"
        @delete-watchlist="emit('delete-watchlist', $event)"
        @add-contract="emit('add-contract', $event)"
        @remove-contract="emit('remove-contract', $event)"
        @reorder-contracts="emit('reorder-contracts', $event)"
      />
      <PositionPanel
        v-else-if="activeSidePanel === PanelTypeEnum.Monitor"
        :contracts="contracts"
        :selected-contract="selectedContract"
        :latest-price="latestPrice"
        @update:selected-contract="emit('update:selectedContract', $event)"
      />
    </div>
    <div class="sidebar-actions">
      <button
        type="button"
        class="sidebar-action"
        :class="{ 'is-active': activeSidePanel === PanelTypeEnum.Contracts }"
        :disabled="!hasContractOptions"
        @click="toggleSidePanel(PanelTypeEnum.Contracts)"
      >
        <el-icon><Collection /></el-icon>
      </button>
      <button
        type="button"
        class="sidebar-action"
        :class="{ 'is-active': activeSidePanel === PanelTypeEnum.Monitor }"
        @click="toggleSidePanel(PanelTypeEnum.Monitor)"
      >
        <el-icon><Monitor /></el-icon>
      </button>
    </div>
  </div>
</template>

<style lang="less" scoped>
.chart-sidebar-box {
  display: flex;
  flex-direction: row;
  gap: .5rem;
  min-height: 0;
  padding: 0.5rem;
}

.sidebar-actions {
  display: flex;
  flex-direction: column;
  row-gap: 2px;
  justify-content: flex-start;
}

.sidebar-action {
  height: 32px;
  padding: 0 10px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #94a3b8;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.sidebar-action:hover:not(:disabled) {
  background: #f1f5f9;
  color: #475569;
}

.sidebar-action.is-active {
  background: #f1f5f9;
  color: #0f172a;
}

.sidebar-action:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.sidebar-action .el-icon {
  font-size: 16px;
}

.sidebar-action-label {
  font-size: 12px;
}

.news-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 10px;
  background: #f8fafc;
}

.panel-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 16px;
  color: #94a3b8;
  font-size: 13px;
  text-align: center;
}
</style>
