<script setup lang="ts">
interface ContractOption {
  label: string
  value: string
  description?: string
}

interface PeriodOption {
  label: string
  value: number | string
}

const emit = defineEmits<{
  'update:selectedContract': [value: string]
  'update:selectedPeriod': [value: number | string]
}>()

withDefaults(
  defineProps<{
    selectedContract?: string
    selectedPeriod?: number | string
    contractOptions?: ContractOption[]
    periodOptions?: PeriodOption[]
    contractLoading?: boolean
    contractDisabled?: boolean
    periodDisabled?: boolean
    contractPlaceholder?: string
  }>(),
  {
    selectedContract: '',
    selectedPeriod: '',
    contractOptions: () => [],
    periodOptions: () => [],
    contractLoading: false,
    contractDisabled: false,
    periodDisabled: false,
    contractPlaceholder: '请选择合约',
  },
)

const handleContractChange = (value: string) => {
  emit('update:selectedContract', value)
}

const handlePeriodChange = (value: number | string) => {
  emit('update:selectedPeriod', value)
}
</script>

<template>
  <div class="future-selector">
    <el-select
      v-if="contractOptions.length"
      :model-value="selectedContract"
      class="selector"
      :placeholder="contractPlaceholder"
      filterable
      :loading="contractLoading"
      :disabled="contractDisabled"
      @update:model-value="handleContractChange"
    >
      <el-option
        v-for="contract in contractOptions"
        :key="contract.value"
        :label="contract.label"
        :value="contract.value"
      >
        <div v-if="contract.description" class="contract-option">
          <span class="contract-symbol">{{ contract.value }}</span>
          <span>·</span>
          <span class="contract-name">{{ contract.description }}</span>
        </div>
        <span v-else>{{ contract.label }}</span>
      </el-option>
    </el-select>

    <el-radio-group
      v-if="periodOptions.length"
      :model-value="selectedPeriod"
      class="period-group"
      :disabled="periodDisabled"
      @update:model-value="handlePeriodChange"
    >
      <el-radio-button
        v-for="period in periodOptions"
        :key="period.value"
        :value="period.value"
      >
        {{ period.label }}
      </el-radio-button>
    </el-radio-group>
  </div>
</template>

<style lang="less" scoped>
.future-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.selector {
  width: 16rem;
}

.contract-option {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.contract-symbol {
  color: #303133;
  font-weight: 600;
}

.contract-name {
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 640px) {
  .selector {
    width: 100%;
  }
}
</style>
