<script setup lang="ts">
import { ElMessage } from "element-plus"
import { storeToRefs } from "pinia"
import { computed, onMounted, ref, watch } from "vue"

import { executePineScannerApi, type PineScannerMatch } from "@/api/modules"
import { usePineScriptsStore } from "@/stores/pineScripts"

const props = defineProps<{
  interval: number
}>()

const emit = defineEmits<{
  "update:selectedContract": [value: string]
}>()

const pineScriptsStore = usePineScriptsStore()
const { loading, scripts } = storeToRefs(pineScriptsStore)
const selectedScriptId = ref<number>()
const scanning = ref(false)
const hasScanned = ref(false)
const scannedCount = ref(0)
const matches = ref<PineScannerMatch[]>([])

const scannerScripts = computed(() => scripts.value.filter((script) => script.script_type === "scanner"))

watch(scannerScripts, (items) => {
  if (selectedScriptId.value && items.some((item) => item.script_id === selectedScriptId.value)) {
    return
  }
  selectedScriptId.value = items[0]?.script_id
}, { immediate: true })

watch(selectedScriptId, () => {
  hasScanned.value = false
  scannedCount.value = 0
  matches.value = []
})

const loadScripts = async () => {
  try {
    await pineScriptsStore.loadScripts()
  } catch {
    ElMessage.error("加载 Pine 扫描器失败。")
  }
}

const scanAllContracts = async () => {
  if (!selectedScriptId.value || scanning.value) {
    return
  }

  scanning.value = true
  try {
    const result = await executePineScannerApi({
      script_id: selectedScriptId.value,
      interval: props.interval,
      limit: 1000,
    })
    scannedCount.value = result.scanned_count
    matches.value = result.matches
    hasScanned.value = true
  } catch (error) {
    const message = error instanceof Error ? error.message : "运行 Pine 扫描器失败。"
    ElMessage.error(message)
  } finally {
    scanning.value = false
  }
}

const formatTriggeredAt = (value: string) => {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false })
}

onMounted(() => {
  void loadScripts()
})
</script>

<template>
  <section class="scanner-panel">
    <header class="panel-header">扫描器</header>
    <div class="scanner-controls">
      <el-select v-model="selectedScriptId" :loading="loading" placeholder="选择扫描器" size="small">
        <el-option
          v-for="script in scannerScripts"
          :key="script.script_id"
          :label="script.script_name"
          :value="script.script_id"
        />
      </el-select>
      <el-button type="primary" size="small" :loading="scanning" :disabled="!selectedScriptId" @click="scanAllContracts">
        扫描全部合约
      </el-button>
    </div>

    <div v-if="hasScanned" class="scanner-summary">命中 {{ matches.length }} 个 / 已扫描 {{ scannedCount }} 个</div>
    <el-scrollbar class="scanner-scrollbar" height="45rem">
      <el-empty v-if="!loading && !scannerScripts.length" description="暂无 Pine 扫描器" :image-size="52" />
      <el-empty v-else-if="hasScanned && !matches.length" description="暂无符合条件的合约" :image-size="52" />
      <button
        v-for="item in matches"
        :key="item.contract_id"
        type="button"
        class="scanner-result"
        @click="emit('update:selectedContract', item.symbol)"
      >
        <div class="scanner-result-header">
          <strong>{{ item.symbol }}</strong>
          <span>{{ item.name }}</span>
        </div>
        <div class="scanner-message">{{ item.message || "SCAN_SIGNAL" }}</div>
        <time>{{ formatTriggeredAt(item.triggered_at) }}</time>
      </button>
    </el-scrollbar>
  </section>
</template>

<style scoped lang="less">
.scanner-panel { width: 18rem; height: 100%; display: flex; flex-direction: column; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; }
.panel-header { padding: 8px 10px; border-bottom: 1px solid #e2e8f0; color: #0f172a; font-size: 14px; font-weight: 600; }
.scanner-controls { display: grid; grid-template-columns: minmax(0, 1fr); gap: 8px; padding: 8px; border-bottom: 1px solid #e2e8f0; }
.scanner-summary { padding: 7px 10px; color: #64748b; font-size: 12px; border-bottom: 1px solid #f1f5f9; }
.scanner-scrollbar { flex: 1; }
.scanner-result { width: 100%; padding: 10px; border: none; border-bottom: 1px solid #f1f5f9; background: transparent; color: #334155; text-align: left; cursor: pointer; }
.scanner-result:hover { background: #f8fafc; }
.scanner-result-header { display: flex; align-items: baseline; gap: 7px; }
.scanner-result-header strong { color: #0f172a; font-size: 14px; }
.scanner-result-header span { min-width: 0; overflow: hidden; color: #64748b; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.scanner-message { margin-top: 5px; overflow: hidden; color: #0369a1; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.scanner-result time { display: block; margin-top: 4px; color: #94a3b8; font-size: 11px; font-variant-numeric: tabular-nums; }
</style>
