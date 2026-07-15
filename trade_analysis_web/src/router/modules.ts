import { type RouteRecordRaw } from "vue-router"

export const RouterModules: RouteRecordRaw[] = [
  {
    path: "/",
    meta: {
      icon: "HomeFilled",
      title: "首页",
    },
    component: () => import("@/views/Home.vue"),
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
        path: "/futures/trade-records",
        component: () => import("@/views/futures/trade_records/TradeRecordSwitcher.vue"),
        meta: {
          icon: "",
          title: "交易记录",
        },
      },
      {
        path: "/futures/opportunity-reviews",
        component: () => import("@/views/futures/opportunity_reviews/OpportunityReviewManager.vue"),
        meta: {
          icon: "",
          title: "机会回顾",
        },
      },
      {
        path: "/futures/trade-thoughts",
        component: () => import("@/views/futures/trade_thoughts/TradeThoughtManager.vue"),
        meta: {
          icon: "",
          title: "交易小记",
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
          title: "期货K线管理",
        },
      },
    ],
  },
]
