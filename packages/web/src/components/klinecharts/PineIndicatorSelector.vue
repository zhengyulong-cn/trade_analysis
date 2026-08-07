<script setup lang="ts">
import { DataAnalysis } from "@element-plus/icons-vue"
import { ElMessage } from "element-plus"
import { storeToRefs } from "pinia"
import { computed } from "vue"

import { usePineScriptsStore } from "@/stores/pineScripts"

const props = withDefaults(
  defineProps<{
    modelValue: number[]
    disabled?: boolean
    loadingIds?: number[]
  }>(),
  {
    disabled: false,
    loadingIds: () => [],
  },
)

const emit = defineEmits<{
  "update:modelValue": [value: number[]]
}>()

const pineScriptsStore = usePineScriptsStore()
const { loading, scripts } = storeToRefs(pineScriptsStore)
const indicatorScripts = computed(() => scripts.value.filter((script) => script.script_type === "indicator"))

const loadScripts = async () => {
  try {
    await pineScriptsStore.loadScripts()
  } catch {
    ElMessage.error("Failed to load Pine indicators.")
  }
}

const updateSelection = (values: Array<string | number | boolean>) => {
  emit("update:modelValue", values.filter((value): value is number => typeof value === "number"))
}
</script>

<template>
  <el-popover placement="bottom-start" :width="320" trigger="click" @show="loadScripts">
    <template #reference>
      <el-button :disabled="disabled" :loading="loading" aria-label="Indicators" title="Indicators">
        <el-icon><DataAnalysis /></el-icon>
      </el-button>
    </template>

    <div v-loading="loading" class="indicator-selector">
      <el-scrollbar max-height="320px">
        <el-checkbox-group :model-value="modelValue" class="indicator-list" @update:model-value="updateSelection">
          <el-checkbox
            v-for="script in indicatorScripts"
            :key="script.script_id"
            :value="script.script_id"
            :disabled="loadingIds.includes(script.script_id)"
            class="indicator-option"
          >
            {{ script.script_name }}
          </el-checkbox>
        </el-checkbox-group>
        <el-empty v-if="!loading && !indicatorScripts.length" description="No Pine indicators" :image-size="52" />
      </el-scrollbar>
    </div>
  </el-popover>
</template>

<style scoped lang="less">
.indicator-selector {
  min-height: 64px;
}

.indicator-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.indicator-option {
  width: 100%;
  min-height: 32px;
  margin-right: 0;
  padding: 6px 4px;
}
</style>
