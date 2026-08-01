<script setup lang="ts">
defineProps<{
  x?: number
  visible: boolean
}>()
</script>

<template>
  <div v-if="visible && x !== undefined" class="replay-selection-marker" :style="{ left: `${x}px` }"></div>
</template>

<style scoped lang="less">
.replay-selection-marker {
  position: absolute;
  z-index: 3;
  top: 0;
  bottom: 0;
  width: 1px;
  pointer-events: none;
  background: #f59e0b;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.7);
}
</style>
