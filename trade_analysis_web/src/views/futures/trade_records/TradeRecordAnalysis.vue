<script lang="ts" setup>
defineProps<{
  handleModeChange: (mode: string | number | boolean) => void
}>()
</script>

<template>
  <section class="trade-record-analysis-page">
    <div class="manager-card">
      <header class="toolbar">
        <div class="toolbar-left">
          <div class="toolbar-title">
            交易记录分析
            <el-icon class="icon" @click="handleModeChange('manager')">
              <Switch />
            </el-icon>
          </div>
        </div>
        <div class="toolbar-right">
          <div class="summary">2 条记录</div>
        </div>
      </header>
    </div>
  </section>
</template>

<style scoped lang="less">
.trade-record-analysis-page {
  padding: 16px;
}

.analysis-card {
  display: flex;
  flex-direction: column;
  row-gap: 12px;
}

.toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.toolbar-left {
  min-width: 0;
}

.toolbar-title {
  display: flex;
  align-items: center;
  column-gap: 4px;
  color: #1a2233;
  font-size: 20px;
  font-weight: 700;
  .icon {
    cursor: pointer;
    &:hover {
        color: #409eff;
    }
  }
}

.toolbar-subtitle {
  margin-top: 4px;
  color: #7d8899;
  font-size: 13px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}
</style>
