import { type RouteRecordRaw } from "vue-router";

export const RouterModules: RouteRecordRaw[] = [
  {
    path: "/",
    redirect: "/futures/monitor",
  },
  {
    path: "/home",
    name: "Home",
    component: () => import("@/views/Home.vue"),
    meta: {
      icon: "HomeFilled",
      title: "首页",
    },
  },
  {
    path: "/futures",
    name: "Futures",
    meta: {
      icon: "TrendCharts",
      title: "期货",
    },
    children: [
      {
        path: "/futures/detail",
        component: () => import("@/views/futures/FutureDetail.vue"),
        meta: {
          icon: "",
          title: "期货单品详情",
        },
      },
    ],
  },
];
