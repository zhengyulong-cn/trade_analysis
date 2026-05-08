<script setup lang="ts">
import { ref } from 'vue'

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

const activeNames = ref<string[]>(['contracts', 'placeholder'])

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
            <span class="contract-code">{{ contract.value }}</span>
            <span class="contract-name">{{ contract.description || contract.label }}</span>
          </button>
        </div>
      </el-collapse-item>

      <el-collapse-item title="合约情况" name="placeholder">
        <div class="placeholder-content"></div>
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
  gap: .5rem;
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
  flex-direction: column;
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
  font-size: 13px;
  font-weight: 600;
}

.contract-name {
  font-size: 12px;
  color: #64748b;
}

.contract-item.is-active .contract-name {
  color: #475569;
}

.placeholder-content {
  min-height: 60px;
}
</style>
