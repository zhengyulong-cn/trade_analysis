import { type RouteRecordRaw } from "vue-router"

export const RouterModules: RouteRecordRaw[] = [
  {
    path: "/",
    redirect: "/futures/detail",
  },
  {
    path: "/home",
    name: "Home",
    component: () => import("@/views/Home.vue"),
    meta: {
      icon: "HomeFilled",
      title: "\u9996\u9875",
    },
  },
  {
    path: "/futures",
    name: "Futures",
    meta: {
      icon: "TrendCharts",
      title: "\u671f\u8d27",
    },
    children: [
      {
        path: "/futures/detail",
        component: () => import("@/views/futures/future_detail/FutureDetail.vue"),
        meta: {
          icon: "",
          title: "K\u7ebf\u884c\u60c5",
        },
      },
      {
        path: "/futures/data_manager",
        component: () => import("@/views/futures/future_data_manager/FutureDataManager.vue"),
        meta: {
          icon: "",
          title: "\u671f\u8d27\u6570\u636e\u7ba1\u7406",
        },
      },
      {
        path: "/futures/contract_manager",
        component: () => import("@/views/futures/future_contracts_manager/FutureContractManager.vue"),
        meta: {
          icon: "",
          title: "\u671f\u8d27\u5408\u7ea6\u7ba1\u7406",
        },
      },
    ],
  },
]
