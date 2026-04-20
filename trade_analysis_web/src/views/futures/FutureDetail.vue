<script lang="ts" setup>
import { getFutureDataApi } from '@/api/modules';
import { onMounted } from 'vue';
onMounted(() => {
  getFutureDataApi({
    symbol: "eb2607",
    period: 60 * 5,
  })
})
</script>

<template>
  <div class="pageBox">
    <div v-for="i in 100">期货单品详情</div>
  </div>
</template>

<style lang="less" scoped>
</style>
