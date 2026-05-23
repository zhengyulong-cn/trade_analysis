<script lang="ts" setup>
const url = '/assets/images/remind.png'
</script>

<template>
  <div class="pageBox home-page">
    <el-image class="page-el-image" :src="url" fit="fill" />
  </div>
</template>

<style lang="less" scoped>
.home-page {
  min-height: calc(100vh - 4rem);
}
.page-el-image {
  width: 100%;
  height: 100%;
}
</style>
