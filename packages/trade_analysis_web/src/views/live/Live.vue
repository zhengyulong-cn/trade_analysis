<script setup lang="ts">
import KLineChartsPanel from "@/components/klinecharts/KLineChartsPanel.vue"
import { useContractsStore } from "@/stores/contracts"
import { ElMessage } from "element-plus"
import { storeToRefs } from "pinia"
import { onMounted, watch } from "vue"

const contractsStore = useContractsStore()
const { contracts, loading, loadError } = storeToRefs(contractsStore)

onMounted(() => {
  void contractsStore.loadContracts()
})

watch(loadError, (message) => {
  if (message) {
    ElMessage.error("获取合约列表失败")
  }
})
</script>

<template>
  <KLineChartsPanel :contracts="contracts" :loading="loading" />
</template>
