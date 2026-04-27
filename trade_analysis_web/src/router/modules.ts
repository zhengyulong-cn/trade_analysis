import { type RouteRecordRaw } from "vue-router"

export const RouterModules: RouteRecordRaw[] = [
  {
    path: "/",
    redirect: "/market_conditions",
  },
  {
    path: "/market_conditions",
    component: () => import("@/views/market_conditions/MarketConditions.vue"),
    meta: {
      icon: "TrendCharts",
      title: "市场行情",
    },
  },
  {
    path: "/futures",
    name: "Futures",
    meta: {
      icon: "Menu",
      title: "期货数据管理",
    },
    children: [
      {
        path: "/futures/contract_manager",
        component: () => import("@/views/futures/future_contracts_manager/FutureContractManager.vue"),
        meta: {
          icon: "",
          title: "期货合约管理",
        },
      },
      {
        path: "/futures/data_manager",
        component: () => import("@/views/futures/future_data_manager/FutureDataManager.vue"),
        meta: {
          icon: "",
          title: "期货数据管理",
        },
      },
      {
        path: "/futures/strategy_analysis_manager",
        component: () => import("@/views/futures/future_strategy_analysis_manager/FutureStrategyAnalysisManager.vue"),
        meta: {
          icon: "",
          title: "期货策略分析管理",
        },
      },
    ],
  },
]
