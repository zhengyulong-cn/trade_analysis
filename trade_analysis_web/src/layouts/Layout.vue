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
      <div class="headerText">Trade Analysis</div>
      <section class="body">
        <Menu class="menu"></Menu>
      </section>
    </header>
    <div class="layoutContent">
      <slot name="layoutContent"></slot>
    </div>
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
    align-items: center;
    width: 100%;
    padding: 0rem 1rem;
    position: fixed;
    border-bottom: 1px solid black;
    background-color: white;

    .headerText {
      font-weight: bold;
    }

    .body {
      flex: 1;
    }
  }

  .layoutContent {
    width: 100%;
    // padding: .5rem 1rem;
    margin-top: 3rem;
  }
}
</style>