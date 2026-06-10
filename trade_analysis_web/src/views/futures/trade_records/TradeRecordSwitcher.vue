<script lang="ts" setup>
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import TradeRecordAnalysis from "./TradeRecordAnalysis.vue"
import TradeRecordManager from "./TradeRecordManager.vue"

type TradeRecordMode = "manager" | "analysis"

const route = useRoute()
const router = useRouter()

const currentMode = computed<TradeRecordMode>(() => {
  const mode = route.query.mode
  return mode === "analysis" ? "analysis" : "manager"
})

const handleModeChange = (mode: string | number | boolean) => {
  router.replace({
    query: {
      ...route.query,
      mode: String(mode) === "analysis" ? "analysis" : "manager",
    },
  })
}
</script>

<template>
  <section class="trade-record-switcher">
    <TradeRecordManager v-if="currentMode === 'manager'" :handle-mode-change="handleModeChange"/>
    <TradeRecordAnalysis v-else :handle-mode-change="handleModeChange" />
  </section>
</template>

<style scoped lang="less">
.trade-record-switcher {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.switcher-toolbar {
  padding: 16px 16px 0;
}
</style>
