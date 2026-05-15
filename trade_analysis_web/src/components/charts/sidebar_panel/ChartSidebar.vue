<script setup lang="ts">
import { ChatDotSquare, Collection } from '@element-plus/icons-vue'
import { computed, ref } from 'vue'
import ContractListPanel from './ContractListPanel.vue'

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
  'toggleFavorite': [value: string]
}>()

const activeSidePanel = ref<'contracts' | 'news' | null>(null)

const hasContractOptions = computed(() => props.contractOptions.length > 0)
const isContractPanelOpen = computed(() => activeSidePanel.value === 'contracts')
const isNewsPanelOpen = computed(() => activeSidePanel.value === 'news')

const toggleSidePanel = (panel: 'contracts' | 'news') => {
  activeSidePanel.value = activeSidePanel.value === panel ? null : panel
}

const handleContractSelect = (contractValue: string) => {
  if (contractValue && contractValue !== props.selectedContract) {
    emit('update:selectedContract', contractValue)
  }
}

const handleToggleFavorite = (contractValue: string) => {
  emit('toggleFavorite', contractValue)
}
</script>

<template>
  <div class="chart-sidebar-box">
    <div v-if="activeSidePanel" class="sidebar-panel-content">
      <ContractListPanel
        v-if="isContractPanelOpen"
        :contract-options="contractOptions"
        :selected-contract="selectedContract"
        @close="toggleSidePanel('contracts')"
        @select="handleContractSelect"
        @toggle-favorite="handleToggleFavorite"
      />

      <div v-else-if="isNewsPanelOpen" class="news-panel">
        <div class="panel-empty">暂无资讯内容</div>
      </div>
    </div>
    <div class="sidebar-actions">
      <button
        type="button"
        class="sidebar-action"
        :class="{ 'is-active': isContractPanelOpen }"
        :disabled="!hasContractOptions"
        @click="toggleSidePanel('contracts')"
      >
        <el-icon><Collection /></el-icon>
      </button>

      <button
        type="button"
        class="sidebar-action"
        :class="{ 'is-active': isNewsPanelOpen }"
        @click="toggleSidePanel('news')"
      >
        <el-icon><ChatDotSquare /></el-icon>
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

.sidebar-panel-content {
  flex: 1;
  min-width: 16rem;
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
