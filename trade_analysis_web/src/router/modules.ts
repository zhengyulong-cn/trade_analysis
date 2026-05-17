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
        path: "/futures/contracts",
        component: () => import("@/views/futures/future_contracts_manager/FutureContractManager.vue"),
        meta: {
          icon: "",
          title: "期货合约管理",
        },
      },
      {
        path: "/futures/contract-prompt-profiles",
        component: () => import("@/views/futures/contract_prompt_profile_manager/ContractPromptProfileManager.vue"),
        meta: {
          icon: "",
          title: "AI画像配置",
        },
      },
      {
        path: "/reports/documents",
        component: () => import("@/views/reports/report_document_manager/ReportDocumentManager.vue"),
        meta: {
          icon: "",
          title: "研报管理",
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
