<script setup lang="ts">
import { computed, ref } from 'vue'
import type { FutureContract } from '@/api/modules'
import { Collection, Monitor } from '@element-plus/icons-vue'
import ContractListPanel from './sidebar_panel/ContractListPanel.vue';

enum PanelTypeEnum {
  Contracts = 'contracts',
  Monitor = 'Monitor',
}

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

const activeSidePanel = ref<PanelTypeEnum | null>(null)
const hasContractOptions = computed(() => props.contracts.length > 0)

const toggleSidePanel = (panel: PanelTypeEnum) => {
  activeSidePanel.value = activeSidePanel.value === panel ? null : panel
}
</script>

<template>
  <div class="chart-sidebar-box">
    <div v-if="activeSidePanel">
      <ContractListPanel v-if="activeSidePanel === PanelTypeEnum.Contracts" :contracts="contracts" :selectedContract="selectedContract" @update:selected-contract="emit('update:selectedContract', $event)"/>
      <section v-else-if="activeSidePanel === PanelTypeEnum.Monitor" class="news-panel">
        <div class="panel-empty">暂无监视</div>
      </section>
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
