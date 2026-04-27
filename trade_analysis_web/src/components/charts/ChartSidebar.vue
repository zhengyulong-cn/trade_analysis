<script setup lang="ts">
import { ChatDotSquare, Collection } from '@element-plus/icons-vue'
import { computed, ref } from 'vue'

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
    <div
      v-if="isContractPanelOpen"
      class="sidebar-panel contract-panel"
    >
      <div class="panel-header">合约列表</div>
      <div class="contract-list">
        <button
          v-for="contract in contractOptions"
          :key="contract.value"
          type="button"
          class="contract-item"
          :class="{ 'is-active': contract.value === selectedContract }"
          @click="handleContractSelect(contract.value)"
        >
          <span class="contract-code">{{ contract.value }}</span>
          <span class="contract-name">{{ contract.description || contract.label }}</span>
        </button>
      </div>
    </div>

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

      <el-tooltip content="快讯" placement="left">
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

.sidebar-actions,
.sidebar-panel {
  pointer-events: auto;
}

.sidebar-actions {
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

.sidebar-panel {
  width: min(240px, calc(100vw - 96px));
  max-height: 100%;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.14);
  backdrop-filter: blur(12px);
  overflow: hidden;
}

.panel-header {
  padding: 12px 14px;
  border-bottom: 1px solid #e5e7eb;
  color: #111827;
  font-size: 13px;
  font-weight: 600;
}

.contract-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
  max-height: calc(100vh - 10rem);
  overflow-y: auto;
}

.contract-item {
  width: 100%;
  border: 1px solid transparent;
  border-radius: 8px;
  background: #f8fafc;
  padding: 10px 12px;
  text-align: left;
  color: #0f172a;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 2px;
  transition: background-color 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}

.contract-item:hover {
  background: #eff6ff;
  border-color: #bfdbfe;
  transform: translateX(-2px);
}

.contract-item.is-active {
  background: #111827;
  border-color: #111827;
  color: #ffffff;
}

.contract-code {
  font-size: 13px;
  font-weight: 600;
}

.contract-name {
  font-size: 12px;
  color: inherit;
  opacity: 0.78;
}

@media (max-width: 768px) {
  .chart-sidebar {
    top: 12px;
    right: 12px;
    left: 12px;
    bottom: auto;
    justify-content: flex-end;
  }

  .sidebar-panel {
    width: min(220px, calc(100vw - 84px));
    max-height: calc(100vh - 11rem);
  }
}
</style>
