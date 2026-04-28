<script setup lang="ts">
import { ChatDotSquare, Collection } from '@element-plus/icons-vue'
import { computed, ref } from 'vue'
import ContractListPanel from './sidebar_panel/ContractListPanel.vue'

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
  'update:selectedContract': [value: string]
}>()

const activeSidePanel = ref<'contracts' | 'news' | null>(null)

const hasContractOptions = computed(() => props.contractOptions.length > 0)

const isContractPanelOpen = computed(() => activeSidePanel.value === 'contracts')

const toggleSidePanel = (panel: 'contracts' | 'news') => {
  activeSidePanel.value = activeSidePanel.value === panel ? null : panel
}

const handleContractSelect = (contractValue: string) => {
  if (contractValue && contractValue !== props.selectedContract) {
    emit('update:selectedContract', contractValue)
  }
}
</script>

<template>
  <div class="chart-sidebar">
    <ContractListPanel
      v-if="isContractPanelOpen"
      :contract-options="contractOptions"
      :selected-contract="selectedContract"
      @close="toggleSidePanel('contracts')"
      @select="handleContractSelect"
    />

    <div class="sidebar-actions">
      <el-tooltip content="合约列表" placement="left">
        <button
          type="button"
          class="sidebar-action"
          :class="{ 'is-active': isContractPanelOpen }"
          :disabled="!hasContractOptions"
          @click="toggleSidePanel('contracts')"
        >
          <el-icon><Collection /></el-icon>
        </button>
      </el-tooltip>

      <el-tooltip content="资讯" placement="left">
        <button
          type="button"
          class="sidebar-action"
          @click="toggleSidePanel('news')"
        >
          <el-icon><ChatDotSquare /></el-icon>
        </button>
      </el-tooltip>
    </div>
  </div>
</template>

<style lang="less" scoped>
.chart-sidebar {
  position: absolute;
  top: 16px;
  right: 16px;
  bottom: 16px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  pointer-events: none;
}

.sidebar-actions {
  pointer-events: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sidebar-action {
  width: 40px;
  height: 40px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  color: #475569;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.1);
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}

.sidebar-action:hover:not(:disabled),
.sidebar-action.is-active {
  background: #111827;
  color: #ffffff;
  border-color: #111827;
}

.sidebar-action:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}

.sidebar-action .el-icon {
  font-size: 18px;
}

@media (max-width: 768px) {
  .chart-sidebar {
    top: 12px;
    right: 12px;
    left: 12px;
    bottom: auto;
    justify-content: flex-end;
  }
}
</style>
