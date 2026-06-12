<script lang="ts" setup>
import type { TradeRecordColumn, TradeRecordColumnOption } from "@/api/modules"
import { computed } from "vue"
import {
  createDefaultFilterCondition,
  getDefaultFilterValue,
  getFilterOperatorOptions,
  type FilterCondition,
  type FilterLogic,
} from "./tradeRecordFilter"
import { Plus } from "@element-plus/icons-vue";

const props = defineProps<{
  filterableColumns: TradeRecordColumn[]
  filterEnabled: boolean
  filterLogic: FilterLogic
  filterConditions: FilterCondition[]
  getColumnOptions: (column: TradeRecordColumn) => TradeRecordColumnOption[]
}>()

const emit = defineEmits<{
  "update:filter-enabled": [value: boolean]
  "update:filter-logic": [value: FilterLogic]
  "update:filter-conditions": [value: FilterCondition[]]
}>()

const hasColumns = computed(() => props.filterableColumns.length > 0)
const activeFilterCount = computed(() => props.filterConditions.length)

const getColumn = (columnKey: string) =>
  props.filterableColumns.find((column) => column.column_key === columnKey) ?? null

const handleFilterEnabledChange = (value: boolean) => {
  emit("update:filter-enabled", value)
}

const handleFilterLogicChange = (value: FilterLogic) => {
  emit("update:filter-logic", value)
}

const handleAddCondition = () => {
  if (!props.filterableColumns.length) {
    return
  }

  emit("update:filter-conditions", [...props.filterConditions, createDefaultFilterCondition(props.filterableColumns)])
}

const handleRemoveCondition = (conditionId: string) => {
  emit(
    "update:filter-conditions",
    props.filterConditions.filter((condition) => condition.id !== conditionId),
  )
}

const handleClearConditions = () => {
  emit("update:filter-conditions", [])
  emit("update:filter-enabled", false)
}

const handleColumnChange = (conditionId: string, columnKey: string) => {
  const column = getColumn(columnKey)
  const nextOperator = getFilterOperatorOptions(column)[0]?.value ?? "eq"

  emit(
    "update:filter-conditions",
    props.filterConditions.map((condition) =>
      condition.id === conditionId
        ? {
            ...condition,
            column_key: columnKey,
            operator: nextOperator,
            value: getDefaultFilterValue(column?.data_type, nextOperator),
          }
        : condition,
    ),
  )
}

const handleOperatorChange = (conditionId: string, operator: FilterCondition["operator"]) => {
  emit(
    "update:filter-conditions",
    props.filterConditions.map((condition) => {
      if (condition.id !== conditionId) {
        return condition
      }

      const column = getColumn(condition.column_key)
      return {
        ...condition,
        operator,
        value: getDefaultFilterValue(column?.data_type, operator),
      }
    }),
  )
}

const handleValueChange = (conditionId: string, value: unknown) => {
  emit(
    "update:filter-conditions",
    props.filterConditions.map((condition) => (condition.id === conditionId ? { ...condition, value } : condition)),
  )
}

const requiresValue = (operator: FilterCondition["operator"]) =>
  !["true", "false", "empty", "not_empty"].includes(operator)
</script>

<template>
  <el-popover placement="bottom-end" :width="760" trigger="click" popper-class="trade-record-filter-popover">
    <template #reference>
      <el-button>
        筛选
        <el-badge :value="activeFilterCount" :hidden="activeFilterCount === 0" class="filter-badge" />
      </el-button>
    </template>

    <div class="filter-panel">
      <div class="filter-toolbar">
        <div class="filter-panel-title">
          设置筛选条件
        </div>
        <div class="filter-actions">
          <el-switch
            :model-value="filterEnabled"
            inline-prompt
            active-text="启用"
            inactive-text="关闭"
            @update:model-value="handleFilterEnabledChange"
          />
          <el-button text :disabled="!activeFilterCount" @click="handleClearConditions">清空</el-button>
        </div>
      </div>

      <template v-if="hasColumns">
        <div v-if="filterConditions.length" class="condition-list">
          <div class="logic-row">
            <span class="logic-label">符合以下</span>
            <el-select
              :model-value="filterLogic"
              class="logic-select"
              size="small"
              @update:model-value="handleFilterLogicChange"
            >
              <el-option label="所有" value="all" />
              <el-option label="任一" value="any" />
            </el-select>
            <span class="logic-label">条件</span>
          </div>
          <div v-for="condition in filterConditions" :key="condition.id" class="condition-row">
            <el-select
              :model-value="condition.column_key"
              class="column-select"
              @update:model-value="handleColumnChange(condition.id, $event)"
            >
              <el-option
                v-for="column in filterableColumns"
                :key="column.column_id"
                :label="column.column_label"
                :value="column.column_key"
              />
            </el-select>

            <el-select
              :model-value="condition.operator"
              class="operator-select"
              @update:model-value="handleOperatorChange(condition.id, $event)"
            >
              <el-option
                v-for="operator in getFilterOperatorOptions(getColumn(condition.column_key))"
                :key="operator.value"
                :label="operator.label"
                :value="operator.value"
              />
            </el-select>

            <div v-if="requiresValue(condition.operator)" class="value-editor">
              <el-switch
                v-if="getColumn(condition.column_key)?.data_type === 'bool'"
                :model-value="Boolean(condition.value)"
                inline-prompt
                active-text="True"
                inactive-text="False"
                @update:model-value="handleValueChange(condition.id, $event)"
              />

              <el-input-number
                v-else-if="getColumn(condition.column_key)?.data_type === 'number'"
                :model-value="condition.value as number | null"
                class="value-input full-width"
                controls-position="right"
                @update:model-value="handleValueChange(condition.id, $event)"
              />

              <el-date-picker
                v-else-if="getColumn(condition.column_key)?.data_type === 'datetime'"
                :model-value="condition.value as string"
                type="datetime"
                value-format="YYYY-MM-DD HH:mm:ss"
                class="value-input full-width"
                @update:model-value="handleValueChange(condition.id, $event)"
              />

              <el-select
                v-else-if="getColumn(condition.column_key)?.data_type === 'single_select'"
                :model-value="condition.value as string"
                class="value-input full-width"
                clearable
                filterable
                @update:model-value="handleValueChange(condition.id, $event)"
              >
                <el-option
                  v-for="option in getColumnOptions(getColumn(condition.column_key)!)"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>

              <el-select
                v-else-if="getColumn(condition.column_key)?.data_type === 'multi_select'"
                :model-value="Array.isArray(condition.value) ? condition.value : []"
                class="value-input full-width"
                clearable
                filterable
                multiple
                collapse-tags
                collapse-tags-tooltip
                @update:model-value="handleValueChange(condition.id, $event)"
              >
                <el-option
                  v-for="option in getColumnOptions(getColumn(condition.column_key)!)"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>

              <el-input
                v-else
                :model-value="String(condition.value ?? '')"
                class="value-input"
                clearable
                @update:model-value="handleValueChange(condition.id, $event)"
              />
            </div>

            <div v-else class="value-editor empty-placeholder">无需填写值</div>

            <el-button text class="remove-button" @click="handleRemoveCondition(condition.id)">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
        </div>

        <div v-else class="empty-state">暂无筛选条件</div>
        <el-button class="add-button" @click="handleAddCondition" :icon="Plus">新增条件</el-button>
      </template>
    </div>
  </el-popover>
</template>

<style scoped lang="less">
.filter-badge {
  display: inline-flex;
  margin-left: 6px;
}

.filter-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.filter-panel-title {
  color: #1a2233;
  font-size: 16px;
  font-weight: 600;
}

.filter-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.logic-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.logic-label {
  color: #334155;
  font-size: 14px;
}

.logic-select {
  width: 92px;
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.condition-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.condition-row {
  display: grid;
  grid-template-columns: 170px 120px minmax(0, 1fr) 36px;
  gap: 10px;
  align-items: center;
}

.column-select,
.operator-select,
.value-input,
.full-width {
  width: 100%;
}

.value-editor {
  min-width: 0;
}

.empty-placeholder {
  color: #94a3b8;
  font-size: 13px;
}

.remove-button {
  justify-self: center;
  color: #64748b;
}

.empty-state {
  color: #94a3b8;
  font-size: 13px;
}

.add-button {
  align-self: flex-start;
}

@media (max-width: 900px) {
  .filter-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .condition-row {
    grid-template-columns: 1fr;
  }

  .remove-button {
    justify-self: flex-start;
  }
}
</style>
