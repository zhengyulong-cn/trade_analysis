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
      icon: "Histogram",
      title: "市场行情",
    },
  },
  {
    path: "/futures",
    name: "Futures",
    meta: {
      icon: "TrendCharts",
      title: "期货市场工具",
    },
    children: [
      {
        path: "/futures/open_opportunity_analysis",
        component: () => import("@/views/futures/open_opportunity_analysis/OpenOpportunityAnalysis.vue"),
        meta: {
          title: "开仓机会分析",
        },
      },
      {
        path: "/futures/trade-records",
        component: () => import("@/views/futures/trade_records/TradeRecordManager.vue"),
        meta: {
          icon: "",
          title: "交易记录",
        },
      },
    ],
  },
  {
    path: "/data_manager",
    meta: {
      icon: "Menu",
      title: "数据管理",
    },
    children: [
      {
        path: "/futures/products",
        component: () => import("@/views/futures/future_products_manager/FutureProductManager.vue"),
        meta: {
          icon: "",
          title: "期货品种管理",
        },
      },
      {
        path: "/futures/contracts",
        component: () => import("@/views/futures/future_contracts_manager/FutureContractManager.vue"),
        meta: {
          icon: "",
          title: "期货合约管理",
        },
      },
      {
        path: "/futures/klines",
        component: () => import("@/views/futures/future_klines_manager/FutureKlinesManager.vue"),
        meta: {
          icon: "",
          title: "期货K管理",
        },
      },
    ],
  },
]
