<script lang="ts" setup>
defineProps<{
  visible: boolean
  loading: boolean
  preview: {
    contract: string
    openDirectionLabel: string
    recordCount: number
    totalLots: number
    earliestOpenTime: string
    latestCloseTime: string
    totalFeeText: string
    totalPnlText: string
  } | null
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'confirm'): void
}>()
</script>

<template>
  <el-dialog :model-value="visible" title="合并确认" width="34rem" @update:model-value="emit('update:visible', $event)">
    <div v-if="preview" class="merge-dialog">
      <p class="merge-dialog__intro">确认将这些记录合并为一条新的手动交易记录？</p>

      <div class="merge-dialog__grid">
        <div class="merge-dialog__item">
          <span class="merge-dialog__label">合约</span>
          <strong class="merge-dialog__value">{{ preview.contract }}</strong>
        </div>
        <div class="merge-dialog__item">
          <span class="merge-dialog__label">开仓方向</span>
          <strong class="merge-dialog__value">{{ preview.openDirectionLabel }}</strong>
        </div>
        <div class="merge-dialog__item">
          <span class="merge-dialog__label">记录数</span>
          <strong class="merge-dialog__value">{{ preview.recordCount }} 条</strong>
        </div>
        <div class="merge-dialog__item">
          <span class="merge-dialog__label">总手数</span>
          <strong class="merge-dialog__value">{{ preview.totalLots }}</strong>
        </div>
        <div class="merge-dialog__item">
          <span class="merge-dialog__label">最早开仓时间</span>
          <strong class="merge-dialog__value">{{ preview.earliestOpenTime }}</strong>
        </div>
        <div class="merge-dialog__item">
          <span class="merge-dialog__label">最晚平仓时间</span>
          <strong class="merge-dialog__value">{{ preview.latestCloseTime }}</strong>
        </div>
        <div class="merge-dialog__item">
          <span class="merge-dialog__label">总手续费</span>
          <strong class="merge-dialog__value">{{ preview.totalFeeText }}</strong>
        </div>
        <div class="merge-dialog__item">
          <span class="merge-dialog__label">总实际盈亏</span>
          <strong class="merge-dialog__value">{{ preview.totalPnlText }}</strong>
        </div>
      </div>

      <div class="merge-dialog__hint">确认后会创建一条新的 `manual` 记录，并删除当前选中的原始记录。</div>
    </div>

    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="emit('confirm')">确认合并</el-button>
    </template>
  </el-dialog>
</template>

<style lang="less" scoped>
.merge-dialog {
  display: grid;
  gap: 16px;
}

.merge-dialog__intro {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  line-height: 1.6;
}

.merge-dialog__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.merge-dialog__item {
  padding: 12px;
  background: linear-gradient(180deg, #fbfdff 0%, #f5f7fa 100%);
  border: 1px solid #e4e7ed;
  border-radius: 10px;
}

.merge-dialog__label {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  color: #909399;
}

.merge-dialog__value {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  word-break: break-word;
}

.merge-dialog__hint {
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.6;
  color: #8a5a00;
  background: #fff7e6;
  border: 1px solid #f5d9a8;
  border-radius: 10px;
}

@media (max-width: 960px) {
  .merge-dialog__grid {
    grid-template-columns: 1fr;
  }
}
</style>
