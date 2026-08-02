<script setup lang="ts">
import { computed, ref } from 'vue';
import { RouterModules } from '@/router/modules'
import SubMenu from './SubMenu.vue';
import { useRoute } from 'vue-router';
const route = useRoute();
const activeMenu = computed(() => (route.meta.activeMenu ? route.meta.activeMenu : route.path) as string);
const subMenuList = computed(() => RouterModules.filter(item => item.meta))
</script>

<template>
  <div class="menuList">
    <el-menu
      class="elMenu"
      mode="horizontal"
      :default-active="activeMenu"
      :collapse="false"
    >
      <SubMenu :menu-list="subMenuList"></SubMenu>
    </el-menu>
  </div>
</template>

<style lang="less" scoped>
.menuList {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  .elMenu {
    height: 3rem;
    border: unset;
  }
  .collapseBtnBox {
    display: flex;
    justify-content: center;
    align-items: center;
    border-right: 1px solid var(--el-border-color);
    .collapseBtn {
      cursor: pointer;
      &:hover {
        color: var(--el-menu-active-color);
      }
    }
  }
}
</style>