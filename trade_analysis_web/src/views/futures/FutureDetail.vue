<script lang="ts" setup>
import { getFutureDataApi } from '@/api/modules';
import { onMounted } from 'vue';
onMounted(() => {
  getFutureDataApi({
    symbol: "eb2607",
    period: 60 * 5,
  })
})
getFutureDataApi
</script>

<template>
  <div class="pageBox">
    <span>期货单品详情</span>
  </div>
</template>

<style lang="less" scoped>
</style>
