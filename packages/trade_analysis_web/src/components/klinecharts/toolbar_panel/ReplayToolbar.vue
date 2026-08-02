<script setup lang="ts">
import { CaretRight, Close, DArrowRight, RefreshLeft, VideoPause } from "@element-plus/icons-vue"
import { REPLAY_SPEED_OPTIONS, type ReplayMode } from "../composables/useKlineReplay"

defineProps<{
  mode: ReplayMode
  disabled: boolean
  startTime: string
  speed: number
}>()

const emit = defineEmits<{
  beginSelection: []
  play: []
  pause: []
  step: []
  exit: []
  updateSpeed: [value: number]
}>()

const updateSpeed = (value: string | number | boolean) => {
  if (typeof value === "number") {
    emit("updateSpeed", value)
  }
}
</script>

<template>
  <div class="replay-controls">
    <el-tooltip v-if="mode === 'live'" content="Replay" placement="bottom">
      <el-button :icon="CaretRight" circle :disabled="disabled" @click="emit('beginSelection')" />
    </el-tooltip>
    <template v-else-if="mode === 'selecting'">
      <el-tag type="warning" effect="plain">{{ startTime }}</el-tag>
      <el-tooltip content="Exit replay" placement="bottom">
        <el-button :icon="Close" circle @click="emit('exit')" />
      </el-tooltip>
    </template>
    <template v-else>
      <el-segmented :model-value="speed" :options="REPLAY_SPEED_OPTIONS" class="replay-speed" @update:model-value="updateSpeed" />
      <el-tooltip :content="mode === 'playing' ? 'Pause replay' : 'Play replay'" placement="bottom">
        <el-button :icon="mode === 'playing' ? VideoPause : CaretRight" circle @click="mode === 'playing' ? emit('pause') : emit('play')" />
      </el-tooltip>
      <el-tooltip content="Next bar" placement="bottom">
        <el-button :icon="DArrowRight" circle @click="emit('step')" />
      </el-tooltip>
      <el-tooltip content="Choose replay start" placement="bottom">
        <el-button :icon="RefreshLeft" circle @click="emit('beginSelection')" />
      </el-tooltip>
      <el-tooltip content="Exit replay" placement="bottom">
        <el-button :icon="Close" circle @click="emit('exit')" />
      </el-tooltip>
    </template>
  </div>
</template>

<style scoped lang="less">
.replay-controls {
  display: flex;
  align-items: center;
  gap: 6px;
}

.replay-speed {
  flex-shrink: 0;
}
</style>
