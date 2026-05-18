export interface FundamentalAnalysisPromptParams {
  productCode: string
  productName: string
  aliasNames: string[]
  reportName?: string
  reportSource?: string
  publishedAt?: string
}

const buildAliasText = (productCode: string, productName: string, aliasNames: string[]) => {
  const keywords = [productCode, productName, ...aliasNames]
    .map((item) => item.trim())
    .filter(Boolean)
  return Array.from(new Set(keywords)).join(" / ")
}

export const buildFundamentalAnalysisPrompt = (params: FundamentalAnalysisPromptParams) => {
  const aliasText = buildAliasText(params.productCode, params.productName, params.aliasNames)
  return `你是一名期货基本面分析助手。请阅读我上传的PDF研报，并只围绕我指定的品种进行分析。
分析品种：${params.productName}
品种代码：${params.productCode}
识别关键词：${aliasText}

要求：
1. 只提取与“${aliasText}”直接相关的内容。
2. 如果研报里还有其他品种，请忽略无关内容。
3. 输出必须是合法 JSON，不要输出 markdown，不要输出代码块，不要输出任何额外解释。
4. 如果某一项在研报中没有明确提及，请填空字符串 ""。
5. 所有结论都尽量基于研报原文，不要脱离原文自由发挥。
6. 字段内容要求简洁、专业、偏交易视角。

请按下面结构输出：

{
  "product_code": "${params.productCode}",
  "product_name": "${params.productName}",
  "supply_side": "",
  "demand_side": "",
  "inventory_side": "",
  "industry_profit": "",
  "substitution_linkage": "",
  "policy_macro": "",
  "conclusion": ""
}
  
分析思路：
1.supply_side：供给端。重点看开工、检修、重启、投产、进口、发运、到港、气候。
2.demand_side：需求端。重点看下游开工、订单、终端消费、季节性变化。
3.inventory_side：库存端。重点看港口库存、厂库、社库、仓单、去库或累库。
4.industry_profit：产业利润。重点看利润、估值、基差、盘面利润、上下游利润分配。
5.substitution_linkage：替代与联动。重点看原油、煤、上下游品种、板块联动、替代关系。
6.policy_macro：政策与宏观。重点看政策、地缘、海外宏观、汇率、大宗环境。
7.conclusion：结论。综合前面各项，输出一句偏交易视角结论，说明整体是偏多、强多、偏空、强空或是震荡。
`
}
