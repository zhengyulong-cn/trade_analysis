<script setup lang="ts">
withDefaults(
  defineProps<{
    visible: boolean
    text: string
    x: number
    y: number
  }>(),
  {
    visible: false,
    text: "",
    x: 0,
    y: 0,
  },
)
</script>

<template>
  <div
    v-if="visible && text"
    class="pine-label-tooltip"
    :style="{ left: `${x}px`, top: `${y}px` }"
    role="tooltip"
  >
    {{ text }}
  </div>
</template>

<style scoped lang="less">
.pine-label-tooltip {
  position: absolute;
  z-index: 4;
  max-width: 240px;
  padding: 6px 8px;
  border: 1px solid rgba(15, 23, 42, .2);
  border-radius: 4px;
  background: rgba(15, 23, 42, .92);
  color: #ffffff;
  font-size: 12px;
  line-height: 1.4;
  pointer-events: none;
  white-space: pre-wrap;
}
</style>
