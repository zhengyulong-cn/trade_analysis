<script setup lang="ts">
import { CircleClose } from '@element-plus/icons-vue'

interface ContractOption {
  label: string
  value: string
  description?: string
  isFavorite?: boolean
}

withDefaults(
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

const handleContractSelect = (contractValue: string) => {
  emit('select', contractValue)
}
</script>

<template>
  <div class="sidebar-panel contract-panel">
    <div class="panel-header">
      <div>合约列表</div>
      <el-icon class="panel-header-close-icon" @click="emit('close')"><CircleClose /></el-icon>
    </div>
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
</template>

<style lang="less" scoped>
.sidebar-panel {
  width: min(240px, calc(100vw - 96px));
  max-height: 100%;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.14);
  backdrop-filter: blur(12px);
  overflow: hidden;
  pointer-events: auto;
}

.panel-header {
  padding: 12px 14px;
  border-bottom: 1px solid #e5e7eb;
  color: #111827;
  font-size: 1rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-header-close-icon {
  cursor: pointer;
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
  .sidebar-panel {
    width: min(220px, calc(100vw - 84px));
    max-height: calc(100vh - 11rem);
  }
}
</style>
