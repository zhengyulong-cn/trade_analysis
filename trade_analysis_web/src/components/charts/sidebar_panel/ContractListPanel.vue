<script setup lang="ts">
import { Star, StarFilled } from '@element-plus/icons-vue'

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
  toggleFavorite: [value: string]
}>()

const handleContractSelect = (contractValue: string) => {
  emit('select', contractValue)
}

const handleToggleFavorite = (contractValue: string) => {
  emit('toggleFavorite', contractValue)
}
</script>

<template>
  <div class="contract-panel">
    <div class="contract-list">
      <button
        v-for="contract in contractOptions"
        :key="contract.value"
        type="button"
        class="contract-item"
        :class="{ 'is-active': contract.value === selectedContract }"
        @click="handleContractSelect(contract.value)"
      >
        <div class="contract-item__header">
          <div class="contract-code">{{ contract.label }}</div>
          <button
            type="button"
            class="favorite-button"
            :class="{ 'favorite-button--active': contract.isFavorite }"
            @click.stop="handleToggleFavorite(contract.value)"
          >
            <el-icon>
              <StarFilled v-if="contract.isFavorite" />
              <Star v-else />
            </el-icon>
          </button>
        </div>
        <div>{{ contract.value }}</div>
      </button>
    </div>
  </div>
</template>

<style lang="less" scoped>
.contract-panel {
  width: 100%;
  height: 100%;
}

.contract-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 100%;
  overflow: auto;
}

.contract-item {
  width: 100%;
  border: none;
  border-radius: 0.5rem;
  background: transparent;
  padding: 0 0.5rem;
  text-align: left;
  color: #0f172a;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  transition: background-color 0.15s ease;
}

.contract-item__header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.contract-item:hover,
.contract-item.is-active {
  background: #f1f5f9;
}

.contract-code {
  font-size: 1rem;
  font-weight: 600;
}

.favorite-button {
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #c0c4cc;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition:
    color 0.2s ease,
    background-color 0.2s ease;
}

.favorite-button:hover {
  color: #e6a23c;
  background: rgba(230, 162, 60, 0.1);
}

.favorite-button--active {
  color: #e6a23c;
}
</style>
