<script setup lang="ts">
import Menu from '@/layouts/components/Menu.vue';
import { useDark, useToggle } from '@vueuse/core';
const isDark = useDark();
const toggleDark = useToggle(isDark)
const changeTheme = () => {
  toggleDark();
}
</script>

<template>
  <div class="layout">
    <header>
      <div class="title">筝语的交易分析</div>
      <el-switch :model-value="isDark" inline-prompt active-text="暗黑模式" inactive-text="普通模式" @change="changeTheme"></el-switch>
    </header>
    <section class="body">
      <Menu class="menu"></Menu>
      <div class="contentBox">
        <slot name="layoutContent"></slot>
      </div>
    </section>
  </div>
</template>

<style scoped lang="less">
.layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  header {
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    height: 2.5rem;
    border-bottom: 1px solid var(--el-border-color);
    .title {
      font-size: 2rem;
      font-family: "kaiti";
    }
  }
  .body {
    display: flex;
    height: calc(100% - 2.5rem);
    .menu {
      width: auto;
    }
    .contentBox {
      padding: .5rem;
      background-color: var(--el-fill-color);
      flex: 1;
    }
  }
}
</style>