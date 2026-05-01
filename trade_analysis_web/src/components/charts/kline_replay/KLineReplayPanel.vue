<script setup lang="ts">
const props = defineProps<{
  isReplayMode: boolean
  isOpen: boolean
  hasReplayNext: boolean
  replayTimeLabel: string
  replaySelectedTime: Date | null
  replaySelectionRange: {
    start: number | null
    end: number | null
  }
}>()

const emit = defineEmits<{
  close: []
  'update:replaySelectedTime': [value: Date | null]
  enterReplayMode: []
  stepReplayForward: []
  exitReplayMode: []
}>()

const isDateDisabled = (date: Date) => {
  const start = props.replaySelectionRange.start
  const end = props.replaySelectionRange.end
  const time = date.getTime()
  if (start === null || end === null) {
    return true
  }
  return time < start || time > end
}
</script>

<template>
  <div v-if="isOpen" class="replay-panel">
    <div class="replay-panel-header">
      <span class="replay-panel-title">复盘</span>
      <el-icon @click="emit('close')"><CircleClose /></el-icon>
    </div>

    <template v-if="!isReplayMode">
      <div class="replay-panel-section">
        <div>起始时间</div>
        <el-date-picker
          :model-value="replaySelectedTime"
          type="datetime"
          format="YYYY-MM-DD HH:mm"
          :clearable="false"
          :editable="false"
          :disabled-date="isDateDisabled"
          @update:model-value="emit('update:replaySelectedTime', $event)"
        />
        <el-button type="primary" @click="emit('enterReplayMode')">开始复盘</el-button>
      </div>
    </template>

    <template v-else>
      <div class="replay-panel-section">
        <div>当前K线：{{ replayTimeLabel || '--' }}</div>
        <el-button type="primary" :disabled="!hasReplayNext" @click="emit('stepReplayForward')">下一根</el-button>
        <el-button type="danger" @click="emit('exitReplayMode')">退出复盘</el-button>
      </div>
    </template>
  </div>
</template>

<style lang="less" scoped>
.replay-panel {
  position: absolute;
  top: 3rem;
  left: 2rem;
  z-index: 30;
  padding: .75rem;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 .75rem 2rem rgba(15, 23, 42, 0.12);
}

.replay-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: .75rem;
}

.replay-panel-title {
  color: #111827;
  font-size: 1rem;
  font-weight: 600;
}

.replay-panel-section {
  display: flex;
  flex-direction: row;
  column-gap: .5rem;
  align-items: center;

  .el-button {
    margin-left: unset;
  }
}
</style>
