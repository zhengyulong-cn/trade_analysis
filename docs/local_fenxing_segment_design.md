# Local Fenxing Segment 设计说明

本文整理 `trade_analysis_web/src/strategy_core/local_fenxing_segment/` 当前已经实现的完整方案。内容以当前代码行为为准，覆盖：

- 原始 K 线与增量更新
- 包含处理与分型构建
- 本级别线段
- 大级别线段
- 交易区间
- TradingView 图表输出

## 1. 模块划分

当前目录下的核心文件如下：

- `types.ts`
  - 定义原始 K 线、合成 K 线、分型、线段、大级别线段、交易区间及各自状态
- `base_fenxing_builder.ts`
  - 原始 K 线增量写入
  - 包含关系处理
  - 在处理后 K 线基础上构建分型
- `base_segment_builder.ts`
  - 基于分型和 EMA20 增量构建本级别线段
- `higher_level_segment_builder.ts`
  - 基于本级别线段和 EMA20/EMA120 关系增量构建大级别线段
- `trading_range_builder.ts`
  - 基于本级别线段和大级别方向构建交易区间
- `local_fenxing_segment_main.ts`
  - TradingView study 主入口
  - 负责状态推进、截断重建、线段绘制与交易区间矩形绘制

## 2. 原始 K 线数据

原始 K 线使用 `FenxingBar` 表示，包含：

- `index`
- `time`
- `open`
- `high`
- `low`
- `close`
- `ema20`
- `ema120`

说明：

- `ema20` 用于本级别分型/线段规则
- `ema120` 用于大级别线段规则
- 两条均线都在 `local_fenxing_segment_main.ts` 中实时计算，再随着 K 线一起传入各 builder

## 3. 增量更新总原则

这个模块的核心要求是：**所有构建逻辑都必须支持增量更新**。

当前总流程：

1. 新 K 线进入时，调用 `upsertFenxingBar(...)`
2. `upsertFenxingBar(...)` 会返回写入类型：
   - `append`
   - `replace_last`
   - `replace_existing`
   - `insert_historical`
3. 如果是 `append`，继续向后推进各状态
4. 如果不是 `append`，说明历史或最后一根发生了修正，需要先截断，再从受影响位置重建

当前主入口的处理顺序是：

1. `truncateFenxingBuildState(...)`
2. `truncateBaseSegmentBuildState(...)`
3. `truncateHigherLevelSegmentBuildState(...)`
4. 重新执行：
   - `advanceFenxingState(...)`
   - `advanceBaseSegmentState(...)`
   - `advanceHigherLevelSegmentState(...)`
5. 交易区间按本级别线段历史结果整体重建或继续增量推进

## 4. 包含处理

### 4.1 包含判定

相邻两根处理后 K 线 `K1`、`K2`，满足以下任一条件即认为有包含关系：

```ts
(K1.high >= K2.high && K1.low <= K2.low)
|| (K1.high <= K2.high && K1.low >= K2.low)
```

### 4.2 递归包含

包含处理是**从左向右递归进行**的，不向左回溯。

流程示意：

1. `K1` 和 `K2` 有包含，合并成 `K'`
2. 如果 `K'` 和 `K3` 仍有包含，则继续合并成 `K''`
3. 如果 `K''` 和 `K4` 仍有包含，则继续合并
4. 直到不再满足包含关系

### 4.3 包含数量上限

递归包含最多允许覆盖 `maxIncludedRawBarCount` 根原始 K 线。

实现判定为：

```ts
second.sourceEndIndex - first.sourceStartIndex + 1 <= maxIncludedRawBarCount
```

超过上限后，不再继续合并，后续 K 线作为新的独立处理后 K 线参与分型判断。

### 4.4 合成方向判定

当前实现中，包含合成的 high/low 规则由**参与合成序列第一根原始 K 线是否在 EMA20 下方**决定。

字段为：

- `firstBarCloseBelowEma20`

一旦某个合成序列确定了这个方向，后续递归合并都沿用同一套规则。

### 4.5 合成 K 线 high/low 规则

#### 情况 A：第一根原始 K 线收盘价在 EMA20 下

- `high = min(all highs)`
- `low = min(all lows)`

两根递归合并时即：

- `high = min(first.high, second.high)`
- `low = min(first.low, second.low)`

#### 情况 B：第一根原始 K 线收盘价在 EMA20 上或等于 EMA20

- `high = max(all highs)`
- `low = max(all lows)`

两根递归合并时即：

- `high = max(first.high, second.high)`
- `low = max(first.low, second.low)`

### 4.6 合成 K 线保留字段

当前 `MergedFenxingBar` 重点保留：

- `high`
- `low`
- `firstBarCloseBelowEma20`
- `highSourceIndex` / `highSourceTime`
- `lowSourceIndex` / `lowSourceTime`
- `sourceStartIndex` / `sourceEndIndex`
- `sourceStartTime` / `sourceEndTime`

说明：

- 当前逻辑中，合成后 K 线的 `open/close` 并不重要
- 分型和线段只依赖 high/low 及其对应的原始 K 线位置

## 5. 分型构建

### 5.1 计算基础

分型不是直接在原始 K 线上计算，而是：

1. 先对原始 K 线做包含处理
2. 再在处理后 K 线序列上构建分型

### 5.2 顶分型

连续 3 根处理后 K 线中，若中间 K 线满足：

- `middle.high >= left.high && middle.high >= right.high`
- `middle.low >= left.low && middle.low >= right.low`

则判定为顶分型。

### 5.3 底分型

连续 3 根处理后 K 线中，若中间 K 线满足：

- `middle.high <= left.high && middle.high <= right.high`
- `middle.low <= left.low && middle.low <= right.low`

则判定为底分型。

### 5.4 分型落点

分型真正落点不是处理中 K 线的逻辑位置，而是对应极值所在的原始 K 线：

- 顶分型使用 `middle.highSourceIndex / middle.highSourceTime / middle.high`
- 底分型使用 `middle.lowSourceIndex / middle.lowSourceTime / middle.low`

因此当前所有后续线段和绘图，都是基于分型极值对应的原始 K 线索引。

### 5.5 分型确认时机

由于分型至少需要 3 根处理后 K 线，因此当前采用“中间 K 线确认”模式：

- 每加入一根新的独立处理后 K 线
- 就检查倒数第二根是否构成分型中心

### 5.6 分型保存

已确认分型保存在：

- `FenxingBuildState.confirmedFenxingSignals`

这是后续本级别线段的直接输入。

## 6. 本级别线段

### 6.1 基础

本级别线段由：

- 已确认分型
- EMA20

共同决定。

### 6.2 上涨线段定义

上涨线段要求：

1. 起点是底分型最低价
2. 该底分型最低价必须低于 EMA20
3. 终点是顶分型最高价
4. 该顶分型最高价必须高于 EMA20
5. 在线段区间内：
   - 不允许有更高的顶分型高于终点
   - 不允许有更低的底分型低于起点

### 6.3 下跌线段定义

下跌线段要求：

1. 起点是顶分型最高价
2. 该顶分型最高价必须高于 EMA20
3. 终点是底分型最低价
4. 该底分型最低价必须低于 EMA20
5. 在线段区间内：
   - 不允许有更高的顶分型高于起点
   - 不允许有更低的底分型低于终点

### 6.4 种子阶段

在还没有活动段时，线段构建先积累：

- `seedBottomFenxingSignal`
- `seedTopFenxingSignal`

直到找到第一组满足条件的顶/底分型，才正式生成第一条活动线段。

### 6.5 活动段延续与反转

#### 当前为上涨段

- 若出现更高顶分型，且仍高于 EMA20，则上涨段延续，更新终点
- 若出现底分型，则尝试以当前上涨段终点作为潜在下跌段起点，判断能否翻成下跌段

#### 当前为下跌段

- 若出现更低底分型，且仍低于 EMA20，则下跌段延续，更新终点
- 若出现顶分型，则尝试以当前下跌段终点作为潜在上涨段起点，判断能否翻成上涨段

结论：

- 下跌段里的更低底分型属于下跌延续
- 上涨段里的更高顶分型属于上涨延续
- 只有反向分型才会触发潜在翻段判断

## 7. 本级别线段最小间距规则

### 7.1 基础规则

当前实现要求：

**起止顶底极值所在原始 K 线之间的距离必须大于 `minBarDistance`**

实现为：

```ts
Math.abs(endSignal.point.index - startSignal.point.index) > minExtremeBarDistance
```

默认 `minBarDistance = 4`，因此默认需要：

- 极值 K 线距离 `> 4`

也就是至少隔开 5 根原始 K 线。

### 7.2 特殊放宽规则

#### 当前活动段是上涨段

如果潜在下跌段终点价格低于当前上涨段起点价格，则允许跳过最小距离限制，直接确认反转。

#### 当前活动段是下跌段

如果潜在上涨段终点价格高于当前下跌段起点价格，则允许跳过最小距离限制，直接确认反转。

这条规则的意义是：

- 当价格已经突破当前活动段起点极值，反转力度足够强
- 这时优先确认反向段，而不是卡在距离限制里

## 8. 大级别线段

### 8.1 基础

大级别线段不再走大级别分型逻辑，而是直接基于：

- 本级别线段
- EMA20 与 EMA120 的相对关系

来构建。

### 8.2 周期定义

定义：

- `EMA20 >= EMA120` 视为 `above`
- `EMA20 < EMA120` 视为 `below`

并映射为方向：

- `above -> up`
- `below -> down`

### 8.3 上涨大级别段构建

当进入 `above` 周期后：

1. 在 `[区间左边界, 当前金叉位置]` 范围内
2. 找本级别线段最低点，作为上涨大级别段起点
3. 再在 `[上涨段起点, 当前推进位置]` 范围内
4. 找本级别线段最高点，作为上涨大级别段终点

### 8.4 下跌大级别段构建

当进入 `below` 周期后：

1. 在 `[区间左边界, 当前死叉位置]` 范围内
2. 找本级别线段最高点，作为下跌大级别段起点
3. 再在 `[下跌段起点, 当前推进位置]` 范围内
4. 找本级别线段最低点，作为下跌大级别段终点

### 8.5 区间左边界

大级别段起点搜索时，左边界取以下两者较右者：

- 最近一条历史大级别段终点
- 最近一次 EMA20/EMA120 周期切换位置

实现中对应：

- `historicalHigherLevelSegments` 的最后一段终点
- `lastCrossBarIndex`

### 8.6 翻段规则

当前实现的关键点不是“均线周期反了就立刻翻段”，而是：

- 当前活动大级别段先继续保留
- 反向周期出现后，先形成“潜在反向段”
- 只有潜在反向段长度达到最小要求，才真正切换到新段
- 若长度不够，则原大级别段继续延续

例如：

1. 当前是大级别下跌段
2. 出现 `EMA20 >= EMA120`
3. 不会立刻翻成上涨段
4. 而是以当前下跌段终点作为潜在上涨段起点
5. 在 `[当前下跌段终点, 当前最新位置]` 范围内找本级别线段最高点
6. 只有当潜在上涨段长度满足最小要求，才真正切换为上涨段
7. 否则当前下跌段继续保持

上涨转下跌完全对称。

### 8.7 大级别段最小跨度

当前代码实现使用：

```ts
Math.abs(segment.end.index - segment.start.index) + 1 >= minBarDistance * 5
```

也就是大级别线段内部原始 K 线数量至少达到：

- `minBarDistance * 5`

说明：

- 当前文档这里描述的是**当前代码实现**
- 不是历史讨论中的中间口径

### 8.8 大级别状态

`HigherLevelSegmentBuildState` 当前包含：

- `activeHigherLevelSegment`
- `historicalHigherLevelSegments`
- `lastCrossBarIndex`
- `lastCrossRelation`
- `processedBarCount`

## 9. 交易区间

### 9.1 基础

交易区间目前只做本级别，不做更高一层的区间。

交易区间的输入是：

- 已确认的本级别历史线段
- 当前可见的大级别线段方向

### 9.2 特征序列

交易区间不是对所有本级别线段一视同仁，而是只使用：

**与当前大级别方向相反的本级别线段**

例如：

- 大级别方向是上涨，则特征序列只取下跌本级别线段
- 大级别方向是下跌，则特征序列只取上涨本级别线段

### 9.3 首次确认交易区间

首次确认区间时，使用三段结构：

- 前一个特征序列
- 中间一段本级别线段
- 当前特征序列

要求：

1. 前后两个特征序列的 `higherDirection` 相同
2. 前后两个特征序列自身方向相同
3. 中间线段方向必须与特征序列方向相反
4. 前后两个特征序列的价格重叠占整个三段结构价格范围的比例 `>= 0.4`

满足后，才生成第一个交易区间。

### 9.4 区间上下边界

交易区间的上下边界不是简单取最高和最低，而是：

- `top = 特征序列高点中的次高值`
- `bottom = 特征序列低点中的次低值`

这样可以避免被单一极端特征序列直接把区间拉坏。

### 9.5 交易区间扩展

已有交易区间后，新特征序列能否继续并入，需要满足：

1. `feature.higherDirection` 与当前区间最后一根特征序列的 `higherDirection` 相同
2. 新特征序列自身价格波动不能过大：
   - `featureRange < rangeHeight * 2`
3. 新特征序列与当前区间的重叠比例 `>= 0.5`

满足后，会重新根据全部特征序列计算新的区间上下边界和左右边界。

### 9.6 首次成区间时的左扩展

这是后续补充进来的规则。

原始逻辑里，交易区间左边界是：

- 第一根特征序列起点

当前已改为：

1. 先算出区间 `top / bottom`
2. 从第一根特征序列起点对应原始 K 线开始向左遍历
3. 只要左边那根 K 线仍与交易区间价格带有交集，就继续左扩
4. 一旦遇到某根 K 线不再与区间价格带相交，停止扩展

当前“仍处于交易区间内部”的实现条件是：

```ts
bar.high >= bottom && bar.low <= top
```

也就是说，K 线只要与区间价格带发生交集，就认为可以继续左扩。

### 9.7 交易区间状态

`TradingRangeBuildState` 当前包含：

- `activeTradingRange`
- `historicalTradingRanges`
- `lastFeatureSegment`
- `pendingGraphicsRefresh`
- `processedBaseSegmentCount`

其中：

- `pendingGraphicsRefresh` 用于控制图形层是否需要重发矩形
- 避免每根 K 线都重复发送同一批 graphics

## 10. 指标输入参数

`local_fenxing_segment_main.ts` 当前对外暴露两个输入：

1. `maxIncludedRawBarCount`
   - 包含递归最多允许覆盖多少根原始 K 线
2. `minBarDistance`
   - 本级别线段起止极值最小距离
   - 同时也参与大级别线段最小跨度计算

当前默认值：

- `maxIncludedRawBarCount = 4`
- `minBarDistance = 4`

## 11. 图表输出

### 11.1 本级别线段

通过以下 plot 输出：

- `segment`
- `segmentOffset`
- `segmentColor`

当前默认颜色：

- `#000000`

### 11.2 大级别线段

通过以下 plot 输出：

- `higherSegment`
- `higherSegmentOffset`
- `higherSegmentColor`

当前默认颜色：

- `#FF00FF`

### 11.3 交易区间矩形

交易区间通过 `study_graphics` 的 `polygons` 输出。

当前配置：

- 样式 id：`tradingRange`
- 图形类型：矩形四点 polygon
- 默认颜色：`#FFCC00`

矩形 4 个点分别为：

1. 左上 `(left.time, top)`
2. 右上 `(right.time, top)`
3. 右下 `(right.time, bottom)`
4. 左下 `(left.time, bottom)`

### 11.4 分型箭头

当前图表层**不再绘制分型箭头**。

原因：

- 分型数据本身保留
- 但箭头绘制容易受 offset 和历史替换影响而错位
- 当前后续逻辑都直接基于分型数据，不依赖箭头显示

## 12. 当前主入口状态管理

`local_fenxing_segment_main.ts` 当前维护：

- `bars`
- `fenxingBuildState`
- `baseSegmentBuildState`
- `higherLevelSegmentBuildState`
- `tradingRangeBuildState`
- `emittedInitialDrawableSegmentStartKey`
- `emittedInitialHigherDrawableSegmentStartKey`
- `lastSettingsKey`

说明：

- `emittedInitialDrawableSegmentStartKey`
  - 控制本级别线段第一次输出起点，之后输出终点
- `emittedInitialHigherDrawableSegmentStartKey`
  - 控制大级别线段第一次输出起点，之后输出终点
- `lastSettingsKey`
  - 输入参数变化时用于触发整套状态重建

## 13. 当前完整流程总结

当前整个模块的最终流程可以概括为：

1. 原始 K 线增量写入
2. 做包含处理
3. 在处理后 K 线上构建分型
4. 基于分型 + EMA20 构建本级别线段
5. 基于本级别线段 + EMA20/EMA120 构建大级别线段
6. 基于本级别线段 + 大级别方向构建交易区间
7. 图上同时输出：
   - 本级别线段
   - 大级别线段
   - 交易区间矩形

这就是 `local_fenxing_segment` 当前代码所对应的完整设计口径。
