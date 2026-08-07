import { createRouter, createWebHistory } from 'vue-router'
import { RouterModules } from "./modules";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [...RouterModules],
})

export default router
