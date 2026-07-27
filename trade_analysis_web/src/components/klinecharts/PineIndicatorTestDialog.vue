<script setup lang="ts">
import { executePineIndicatorApi, type PineIndicatorExecuteResult } from "@/api/modules"
import { ElMessage } from "element-plus"
import { computed, ref } from "vue"

const props = defineProps<{
  symbol: string
  interval: number
}>()

const visible = ref(false)
const scriptId = ref<number>()
const loading = ref(false)
const result = ref<PineIndicatorExecuteResult>()
const errorMessage = ref("")

const resultText = computed(() => (result.value ? JSON.stringify(result.value, null, 2) : ""))

const open = () => {
  result.value = undefined
  errorMessage.value = ""
  visible.value = true
}

const getErrorMessage = (error: unknown) => {
  if (typeof error === "object" && error !== null && "data" in error) {
    const data = error.data
    if (typeof data === "object" && data !== null && "detail" in data && typeof data.detail === "string") {
      return data.detail
    }
  }
  return "Indicator execution failed."
}

const execute = async () => {
  if (!props.symbol) {
    ElMessage.warning("Select a contract first.")
    return
  }
  if (!scriptId.value) {
    ElMessage.warning("Enter an indicator script ID.")
    return
  }

  loading.value = true
  result.value = undefined
  errorMessage.value = ""
  try {
    result.value = await executePineIndicatorApi({
      script_id: scriptId.value,
      symbol: props.symbol,
      interval: props.interval,
      limit: 1000,
    })
    ElMessage.success("Indicator executed.")
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
    ElMessage.error(errorMessage.value)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <el-button :disabled="!symbol" @click="open">Pine Test</el-button>

  <el-dialog v-model="visible" title="Pine Indicator Test" width="720px" destroy-on-close>
    <el-descriptions :column="2" border size="small">
      <el-descriptions-item label="Contract">{{ symbol || "-" }}</el-descriptions-item>
      <el-descriptions-item label="Interval">{{ interval }}s</el-descriptions-item>
    </el-descriptions>

    <div class="test-controls">
      <el-input-number v-model="scriptId" :min="1" :step="1" controls-position="right" placeholder="Indicator ID" />
      <el-button type="primary" :loading="loading" @click="execute">Execute</el-button>
    </div>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" show-icon />
    <pre v-if="resultText" class="result-output">{{ resultText }}</pre>
  </el-dialog>
</template>

<style scoped lang="less">
.test-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 16px 0;
}

.result-output {
  max-height: 420px;
  margin: 16px 0 0;
  padding: 12px;
  overflow: auto;
  border: 1px solid #dfe5ef;
  border-radius: 6px;
  background: #f8fafc;
  color: #1f2937;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
