<script setup lang="ts">
defineProps<{
  visible: boolean
  x: number
  y: number
  canCreate: boolean
  canDelete: boolean
}>()

const emit = defineEmits<{
  create: []
  delete: []
}>()
</script>

<template>
  <div
    v-if="visible"
    class="chart-context-menu"
    :style="{ left: `${x}px`, top: `${y}px` }"
    @click.stop
  >
    <button
      class="chart-context-menu__item"
      type="button"
      :disabled="!canCreate"
      @click="emit('create')"
    >
      创建线段
    </button>
    <button
      class="chart-context-menu__item"
      type="button"
      :disabled="!canDelete"
      @click="emit('delete')"
    >
      删除线段
    </button>
  </div>
</template>

<style lang="less" scoped>
.chart-context-menu {
  position: absolute;
  z-index: 4;
  min-width: 112px;
  padding: 6px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.16);
}

.chart-context-menu__item {
  display: block;
  width: 100%;
  padding: 7px 10px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #303133;
  font-size: 13px;
  line-height: 1.2;
  text-align: left;
  cursor: pointer;
}

.chart-context-menu__item:hover:not(:disabled) {
  background: #f5f7fa;
}

.chart-context-menu__item:disabled {
  color: #c0c4cc;
  cursor: not-allowed;
}
</style>
