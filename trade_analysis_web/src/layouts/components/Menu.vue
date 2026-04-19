<script setup lang="ts">
import { computed, ref } from 'vue';
import { RouterModules } from '@/router/modules'
import SubMenu from './SubMenu.vue';
import { useRoute } from 'vue-router';
const route = useRoute();
const isCollapse = ref(true)
const activeMenu = computed(() => (route.meta.activeMenu ? route.meta.activeMenu : route.path) as string);
const subMenuList = computed(() => RouterModules.filter(item => item.meta))
const handleCollapse = () => {
  isCollapse.value = !isCollapse.value
}
</script>

<template>
  <div class="menuList">
    <el-menu
      class="elMenu"
      :default-active="activeMenu"
      :collapse="isCollapse"
    >
      <SubMenu :menu-list="subMenuList"></SubMenu>
    </el-menu>
    <div class="collapseBtnBox">
      <el-icon class="collapseBtn" :size="24" @click="handleCollapse">
        <DArrowLeft v-if="!isCollapse"/>
        <DArrowRight v-else />
      </el-icon>
    </div>
  </div>
</template>

<style lang="less" scoped>
.menuList {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  .elMenu {
    height: 100%;
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