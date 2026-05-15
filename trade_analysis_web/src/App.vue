<script setup lang="ts">
import Layout from "./layouts/Layout.vue";
import { useContractsStore } from  '@/stores/contracts'

const initAll = () => {
  const contractsStore = useContractsStore()
  contractsStore.loadContracts()
}
initAll()
</script>

<template>
  <Layout>
    <template v-slot:layoutContent>
      <router-view />
    </template>
  </Layout>
</template>

<style scoped lang="less">
</style>
