<script setup lang="ts">
import { ElMessage } from "element-plus"
import { storeToRefs } from "pinia"
import { computed, onMounted, ref, watch } from "vue"

import { executePineScannerApi, type PineScannerMatch } from "@/api/modules"
import { usePineScriptsStore } from "@/stores/pineScripts"

const SCANNER_CACHE_PREFIX = "pulse:pine-scanner"

interface ScannerCache {
  scriptId: number
  interval: number
  scriptUpdatedAt: string
  scannedCount: number
  matches: PineScannerMatch[]
  updatedAt: string
}

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
const scannedAt = ref<string>()

const scannerScripts = computed(() => scripts.value.filter((script) => script.script_type === "scanner"))
const selectedScript = computed(() => (
  scannerScripts.value.find((script) => script.script_id === selectedScriptId.value)
))

const cacheKey = (scriptId: number, interval: number) => `${SCANNER_CACHE_PREFIX}:${scriptId}:${interval}`

const clearScanResult = () => {
  hasScanned.value = false
  scannedCount.value = 0
  matches.value = []
  scannedAt.value = undefined
}

const restoreCachedResult = () => {
  const script = selectedScript.value
  if (!script) {
    clearScanResult()
    return
  }

  try {
    const key = cacheKey(script.script_id, props.interval)
    const rawCache = window.localStorage.getItem(key)
    if (!rawCache) {
      clearScanResult()
      return
    }

    const cache = JSON.parse(rawCache) as ScannerCache
    if (
      cache.scriptId !== script.script_id
      || cache.interval !== props.interval
      || cache.scriptUpdatedAt !== script.updated_at
      || !Array.isArray(cache.matches)
      || typeof cache.scannedCount !== "number"
      || typeof cache.updatedAt !== "string"
    ) {
      window.localStorage.removeItem(key)
      clearScanResult()
      return
    }

    scannedCount.value = cache.scannedCount
    matches.value = cache.matches
    scannedAt.value = cache.updatedAt
    hasScanned.value = true
  } catch {
    clearScanResult()
  }
}

const persistScanResult = () => {
  const script = selectedScript.value
  if (!script || !scannedAt.value) {
    return
  }

  const cache: ScannerCache = {
    scriptId: script.script_id,
    interval: props.interval,
    scriptUpdatedAt: script.updated_at,
    scannedCount: scannedCount.value,
    matches: matches.value,
    updatedAt: scannedAt.value,
  }
  window.localStorage.setItem(cacheKey(script.script_id, props.interval), JSON.stringify(cache))
}

watch(scannerScripts, (items) => {
  if (selectedScriptId.value && items.some((item) => item.script_id === selectedScriptId.value)) {
    return
  }
  selectedScriptId.value = items[0]?.script_id
}, { immediate: true })

watch([selectedScriptId, () => props.interval, selectedScript], restoreCachedResult)

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
    scannedAt.value = new Date().toISOString()
    hasScanned.value = true
    persistScanResult()
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

const formatDateTime = (value?: string) => (value ? formatTriggeredAt(value) : "-")

onMounted(() => {
  void loadScripts().then(restoreCachedResult)
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
    <div v-if="selectedScript" class="scanner-script-meta">
      <span>Script updated: {{ formatDateTime(selectedScript.updated_at) }}</span>
      <span v-if="scannedAt">Scan updated: {{ formatDateTime(scannedAt) }}</span>
    </div>
    <div class="scanner-scrollbar-wrapper">
      <el-scrollbar class="scanner-scrollbar">
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
    </div>
  </section>
</template>

<style scoped lang="less">
.scanner-panel { width: 18rem; height: 100%; display: flex; flex-direction: column; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; }
.panel-header { padding: 8px 10px; border-bottom: 1px solid #e2e8f0; color: #0f172a; font-size: 14px; font-weight: 600; }
.scanner-controls { 
  display: flex;
  flex-direction: row;
  column-gap: .5rem;
  margin: .5rem .5rem;
}
.scanner-summary { padding: 7px 10px; font-size: 12px;}
.scanner-script-meta { display: grid; gap: 3px; padding: 7px 10px; color: #94a3b8; font-size: 11px; font-variant-numeric: tabular-nums; }
.scanner-scrollbar-wrapper { flex: 1; }
.scanner-result { width: 100%; padding: 10px; border: none; border-bottom: 1px solid #f1f5f9; background: transparent; color: #334155; text-align: left; cursor: pointer; }
.scanner-result:hover { background: #f8fafc; }
.scanner-result-header { display: flex; align-items: baseline; gap: 7px; }
.scanner-result-header strong { color: #0f172a; font-size: 14px; }
.scanner-result-header span { min-width: 0; overflow: hidden; color: #64748b; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.scanner-message { margin-top: 5px; overflow: hidden; color: #0369a1; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.scanner-result time { display: block; margin-top: 4px; color: #94a3b8; font-size: 11px; font-variant-numeric: tabular-nums; }
</style>
