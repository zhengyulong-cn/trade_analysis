<script lang="ts" setup>
import type { TradeRecordColumn } from "@/api/modules"
import { computed, ref } from "vue"
import { createSortCondition, type SortCondition, type SortDirection } from "./tradeRecordSort"
import { Plus } from "@element-plus/icons-vue";

const props = defineProps<{
  sortableColumns: TradeRecordColumn[]
  sortEnabled: boolean
  sortConditions: SortCondition[]
}>()

const emit = defineEmits<{
  "update:sortEnabled": [value: boolean]
  "update:sortConditions": [value: SortCondition[]]
}>()

const visible = ref(false)

const activeSortCount = computed(() => props.sortConditions.length)

const getSortDirectionOptions = (columnKey: string) => {
  const column = props.sortableColumns.find((item) => item.column_key === columnKey)

  if (column?.data_type === "string") {
    return [
      { label: "A -> Z", value: "asc" },
      { label: "Z -> A", value: "desc" },
    ]
  }

  if (column?.data_type === "datetime") {
    return [
      { label: "时间升序", value: "asc" },
      { label: "时间降序", value: "desc" },
    ]
  }

  return [
    { label: "0 -> 9", value: "asc" },
    { label: "9 -> 0", value: "desc" },
  ]
}

const updateSortEnabled = (value: boolean) => {
  emit("update:sortEnabled", value)
}

const addSortCondition = () => {
  if (!props.sortableColumns.length) {
    return
  }

  emit("update:sortConditions", [...props.sortConditions, createSortCondition(props.sortableColumns)])
  emit("update:sortEnabled", true)
}

const removeSortCondition = (conditionId: string) => {
  emit(
    "update:sortConditions",
    props.sortConditions.filter((item) => item.id !== conditionId),
  )
}

const clearSortConditions = () => {
  emit("update:sortConditions", [])
}

const updateConditionColumn = (conditionId: string, columnKey: string) => {
  emit(
    "update:sortConditions",
    props.sortConditions.map((item) => (item.id === conditionId ? { ...item, column_key: columnKey } : item)),
  )
}

const updateConditionDirection = (conditionId: string, direction: SortDirection) => {
  emit(
    "update:sortConditions",
    props.sortConditions.map((item) => (item.id === conditionId ? { ...item, direction } : item)),
  )
}
</script>

<template>
  <el-popover v-model:visible="visible" placement="bottom-end" :width="520" trigger="click">
    <template #reference>
      <el-button>
        排序
        <el-badge v-if="activeSortCount" :value="activeSortCount" class="sort-badge" />
      </el-button>
    </template>

    <div class="sort-panel">
      <div class="sort-panel-header">
        <div class="sort-panel-title">设置排序条件</div>
        <div class="sort-action">
          <el-switch
            :model-value="sortEnabled"
            inline-prompt
            active-text="开"
            inactive-text="关"
            @update:model-value="updateSortEnabled"
          />
          <el-button text @click="clearSortConditions" :disabled="!activeSortCount">清空</el-button>
        </div>
      </div>

      <div v-if="sortConditions.length" class="sort-condition-list">
        <div v-for="condition in sortConditions" :key="condition.id" class="sort-condition-item">
          <el-select
            :model-value="condition.column_key"
            class="sort-column-select"
            @update:model-value="updateConditionColumn(condition.id, String($event))"
          >
            <el-option
              v-for="column in sortableColumns"
              :key="column.column_key"
              :label="column.column_label"
              :value="column.column_key"
            />
          </el-select>

          <el-segmented
            :model-value="condition.direction"
            class="sort-direction"
            :options="getSortDirectionOptions(condition.column_key)"
            @update:model-value="updateConditionDirection(condition.id, $event as SortDirection)"
          />

          <el-button text @click="removeSortCondition(condition.id)">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </div>

      <div v-else class="empty-state">暂无排序条件</div>

      <div class="sort-panel-actions">
        <el-button @click="addSortCondition" :icon="Plus">新增条件</el-button>
      </div>
    </div>
  </el-popover>
</template>

<style scoped lang="less">
.sort-badge {
  margin-left: 6px;
}

.sort-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sort-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sort-panel-title {
  color: #1a2233;
  font-size: 16px;
  font-weight: 600;
}

.sort-action {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sort-condition-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sort-condition-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 12px;
  align-items: center;
}

.sort-column-select {
  width: 100%;
}

.sort-direction {
  min-width: 170px;
}

.empty-state {
  color: #94a3b8;
  font-size: 13px;
}

.sort-panel-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

@media (max-width: 900px) {
  .sort-condition-item {
    grid-template-columns: 1fr;
  }
}
</style>
