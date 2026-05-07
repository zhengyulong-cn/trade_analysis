# Local Fenxing Segment 方案整理

本文整理今天在 `trade_analysis_web/src/strategy_core/local_fenxing_segment/` 中最终敲定的分型、包含、线段相关方案。内容以当前实现和最终确认的业务规则为准，后续继续扩展时应以本文作为基线。

## 1. 模块划分

当前目录下的职责划分如下：

- `types.ts`
  - 定义 K 线、合成 K 线、分型、线段、构建状态等类型
- `base_fenxing_builder.ts`
  - 负责原始 K 线增量写入
  - 负责包含关系处理
  - 负责在处理后的 K 线基础上构建分型
- `base_segment_builder.ts`
  - 负责在分型和 EMA20 基础上增量构建本级别线段
- `local_fenxing_segment_main.ts`
  - TradingView 指标主入口
  - 管理运行时状态
  - 将原始 K 线喂给 fenxing/segment builder
  - 当前只绘制线段，不再绘制分型箭头

## 2. 原始 K 线数据

单根原始 K 线使用 `FenxingBar` 表示，字段包括：

- `index`: 当前原始 K 线序号
- `time`: 时间
- `open`
- `high`
- `low`
- `close`
- `ema20`

其中 `ema20` 是在主入口中按每根 K 线实时计算后，随 K 线一起传入后续构建逻辑。

## 3. 增量更新总原则

今天确认的一个核心要求是：**所有逻辑都必须支持增量更新**。

当前实现按下面方式工作：

1. 新 K 线到来时，先调用 `upsertFenxingBar(...)`
2. `upsertFenxingBar(...)` 支持 4 种情况：
   - `append`: 新增最新 K 线
   - `replace_last`: 替换最后一根 K 线
   - `replace_existing`: 替换历史中某一根同时间 K 线
   - `insert_historical`: 插入一根历史 K 线
3. 如果是 `append`，继续向后增量推进
4. 如果不是 `append`，先截断已有状态，再从受影响位置重新增量计算：
   - `truncateFenxingBuildState(...)`
   - `truncateBaseSegmentBuildState(...)`
5. 然后继续执行：
   - `advanceFenxingState(...)`
   - `advanceBaseSegmentState(...)`

这样做的目的，是在保留增量效率的同时，允许最后一根或历史数据被修正后，后续结果仍然正确。

## 4. 包含关系处理

### 4.1 包含判定

相邻两根处理后 K 线 `K1`、`K2`，满足以下任一条件，则认为存在包含关系：

```ts
(K1.high >= K2.high && K1.low <= K2.low)
|| (K1.high <= K2.high && K1.low >= K2.low)
```

### 4.2 递归包含

包含处理是**从左向右递归进行**的，不向左回溯。

示意如下：

1. `K1` 和 `K2` 有包含，合并为 `K'`
2. 若 `K'` 和 `K3` 仍有包含，则继续合并为 `K''`
3. 若 `K''` 和 `K4` 仍有包含，则继续合并为 `K'''`
4. 以此类推，直到不再满足包含条件

注意点：

- 只会拿“当前最后一根处理后 K 线”和“新来的这一根 K 线”做判断
- 不会为了新结果回头重新向左扫描整个序列

### 4.3 包含处理上限

递归包含增加了上限约束：**最多处理 `maxIncludedRawBarCount` 根原始 K 线**。

当前实现判定方式为：

```ts
second.sourceEndIndex - first.sourceStartIndex + 1 <= maxIncludedRawBarCount
```

也就是说：

- 若当前合并结果覆盖的原始 K 线数量没有超过上限，则允许继续合并
- 一旦超过上限，则停止递归包含，后续 K 线作为新的独立处理后 K 线参与分型计算

### 4.4 合成 K 线方向判定依据

今天最终确认：**合成时看第一根 K 线是否在 EMA20 上下**。

实现中使用的是：

- `firstBarCloseBelowEma20`

即以参与该次合并序列中的**第一根原始 K 线的收盘价**是否低于其 EMA20，来确定后续整个合成过程使用哪一套 high/low 规则。

### 4.5 合成 K 线 high/low 规则

最终敲定方案如下，这也是今天最后确认的缠论定义口径：

#### 情况 A：第一根 K 线收盘价在 EMA20 下

合成后的新 K 线：

- `high = 用到合成的所有 K 线最高价中的最低价`
- `low = 用到合成的所有 K 线最低价中的最低价`

对应到两根递归合并时，就是：

- `high = min(first.high, second.high)`
- `low = min(first.low, second.low)`

#### 情况 B：第一根 K 线收盘价在 EMA20 上或等于 EMA20

合成后的新 K 线：

- `high = 用到合成的所有 K 线最高价中的最高价`
- `low = 用到合成的所有 K 线最低价中的最高价`

对应到两根递归合并时，就是：

- `high = max(first.high, second.high)`
- `low = max(first.low, second.low)`

### 4.6 合成 K 线 open/close 是否重要

今天已确认：**`MergedFenxingBar` 中 `open/close` 并不重要，核心只需要 `high/low`**。

因此当前合成 K 线主要保留：

- `high`
- `low`
- `firstBarCloseBelowEma20`
- 极值对应的原始 K 线索引和时间
- 合并覆盖范围的起止原始 K 线索引和时间

这样做是因为分型和后续线段构建都依赖极值位置，不依赖合成后 K 线的开收盘。

## 5. 分型构建

### 5.1 分型的计算基础

分型不是在原始 K 线上直接算，而是：

1. 先对原始 K 线做包含处理
2. 再在“处理后的 K 线序列”上构建分型

### 5.2 分型定义

连续 3 根处理后 K 线，取中间一根作为候选分型。

#### 顶分型

中间 K 线同时满足：

- `middle.high >= left.high && middle.high >= right.high`
- `middle.low >= left.low && middle.low >= right.low`

则为顶分型。

#### 底分型

中间 K 线同时满足：

- `middle.high <= left.high && middle.high <= right.high`
- `middle.low <= left.low && middle.low <= right.low`

则为底分型。

### 5.3 分型极值落点

今天我们也明确了，分型真正落点不是中间处理后 K 线的“处理后序号”，而是它对应极值所在的原始 K 线：

- 顶分型取 `middle.highSourceIndex / highSourceTime / high`
- 底分型取 `middle.lowSourceIndex / lowSourceTime / low`

这也是之前图表箭头错位问题的根源之一：图上如果直接按旧索引绘制，视觉上会偏一根甚至多根。

### 5.4 分型是否保存

已确认：**分型会保存下来**，因为后续还要基于分型构建线段。

当前保存在：

- `FenxingBuildState.confirmedFenxingSignals`

每个分型信号 `FenxingSignal` 主要包含：

- `type`: `top` / `bottom`
- `point`: 分型极值点
- `mergedBarIndex`: 分型对应的处理中 K 线位置
- `sourceStartIndex/sourceEndIndex`
- `sourceStartTime/sourceEndTime`

变量名也已按今天确认过的要求统一为：

- `confirmedFenxingSignals`

而不是更模糊的 `confirmedSignals`。

### 5.5 分型确认时机

由于分型最少需要 3 根处理后 K 线，因此采用“中间 K 线确认”的方式：

- 当最新处理后 K 线加入后，检查倒数第二根是否构成分型中心
- 若成立，则追加到 `confirmedFenxingSignals`

## 6. 图表展示与分型箭头

今天最终确认：**图表中不再绘制分型箭头，当前只画线段**。

原因是：

- 分型数据本身是正确的
- 但 TradingView 图表中的箭头绘制容易因索引/offset 处理导致错位
- 用户后续准备自己直接画线，因此已将箭头绘制逻辑移除

所以当前状态是：

- `confirmedFenxingSignals` 仍然保留，供线段构建使用
- 图表层不再输出 `↑ / ↓` 标记

## 7. 本级别线段构建

### 7.1 基础

本级别线段以两部分为基础：

- 已确认分型
- EMA20

由 `base_segment_builder.ts` 负责增量构建。

### 7.2 上涨线段定义

上涨线段需要满足：

1. 起点是底分型最低价
2. 该底分型最低价必须低于 EMA20
3. 终点是顶分型最高价
4. 该顶分型最高价必须高于 EMA20
5. 在线段区间内：
   - 不允许有更高的顶分型高于终点
   - 不允许有更低的底分型低于起点

### 7.3 下跌线段定义

下跌线段需要满足：

1. 起点是顶分型最高价
2. 该顶分型最高价必须高于 EMA20
3. 终点是底分型最低价
4. 该底分型最低价必须低于 EMA20
5. 在线段区间内：
   - 不允许有更高的顶分型高于起点
   - 不允许有更低的底分型低于终点

### 7.4 当前活动段的延续规则

这一条今天非常关键，最终口径如下：

#### 当前活动段为上涨段

- 若后面出现更高的顶分型，且该顶分型仍高于 EMA20，则**上涨段继续延伸终点**
- 若后面出现底分型，则把当前上涨段的终点顶分型视为潜在下跌段起点，尝试判断是否能反转成下跌段

#### 当前活动段为下跌段

- 若后面出现更低的底分型，且该底分型仍低于 EMA20，则**下跌段继续延伸终点**
- 若后面出现顶分型，则把当前下跌段的终点底分型视为潜在上涨段起点，尝试判断是否能反转成上涨段

换句话说：

- 下跌段里，更低的底分型属于**下跌延续**
- 上涨段里，更高的顶分型属于**上涨延续**
- 反向分型才用于尝试切换新段

## 8. 线段最小间距规则

### 8.1 当前最终规则

原先讨论过“顶底分型之间不能共用 K 线”的版本，后来已改成现在这版：

**要求底分型最低价所在 K 线与顶分型最高价所在 K 线之间的最小间距大于 `minBarDistance` 根 K 线。**

当前实现为：

```ts
Math.abs(endSignal.point.index - startSignal.point.index) > minExtremeBarDistance
```

默认情况下，`minBarDistance = 4`，因此要求极值 K 线距离必须：

- `> 4`

也就是至少隔开 5 根。

### 8.2 特殊放宽规则

今天又新增了一个特殊情况：

#### 当前构建段是上涨段时

如果潜在下跌段终点价格**低于当前上涨段起点价格**，那么：

- 无论间距是否满足最小 K 线距离要求
- 都允许构建这个下跌反转段

#### 当前构建段是下跌段时

如果潜在上涨段终点价格**高于当前下跌段起点价格**，那么：

- 无论间距是否满足最小 K 线距离要求
- 都允许构建这个上涨反转段

这条规则的本质是：

- 当价格已经有效突破了当前活动段的起点极值，说明反转力度足够强
- 此时可以跳过最小间距约束，优先确认反向段

## 9. 线段状态管理

线段构建状态 `BaseSegmentBuildState` 当前包括：

- `activeBaseSegment`
  - 当前正在延续或等待反转的活动段
- `historicalBaseSegments`
  - 已完成并确认的历史段
- `processedFenxingSignalCount`
  - 已处理到第几个分型信号
- `seedBottomFenxingSignal`
  - 尚未成段时，记录候选底分型种子
- `seedTopFenxingSignal`
  - 尚未成段时，记录候选顶分型种子

其逻辑分为两部分：

1. **seed 阶段**
   - 还没有活动段时，先积累可作为起点的顶/底分型
2. **active 段阶段**
   - 已有活动段时，继续判断是延伸还是反转

## 10. 指标主入口当前输入项

`local_fenxing_segment_main.ts` 当前对外暴露两个输入参数：

1. `maxIncludedRawBarCount`
   - 包含递归最多允许覆盖多少根原始 K 线
2. `minBarDistance`
   - 构建线段时，起止极值 K 线的最小距离约束

当前默认值都为 `4`。

## 11. 图表当前输出

当前指标主入口只输出线段相关序列：

- `segment`
- `segmentOffset`
- `segmentColor`

即：

- 用 price plot 画线段
- 用 data offset 把起点/终点投到正确 K 线位置
- 用 colorer 控制颜色

分型箭头相关输出已经去掉。

## 12. 当前已经明确但尚未展开的大级别方向

今天对大级别也有一个阶段性结论：

- **大级别可以先忽略分型逻辑**
- **直接以本级别线段 + EMA120 来构建**

这个结论目前属于后续实现方向，不属于当前代码里已经完成的内容。但它是今天沟通后的明确方向，后续做大级别线段时建议按这个思路继续推进。

## 13. 当前方案总结

今天最终敲定的本级别方案可以概括为：

1. 原始 K 线增量写入
2. 按“相邻包含 + 左到右递归 + 根数上限”做包含处理
3. 合成方向由第一根 K 线是否在 EMA20 下决定
4. 在处理后的 K 线上构建顶底分型
5. 分型信号持久保存为 `confirmedFenxingSignals`
6. 再用分型 + EMA20 增量构建本级别线段
7. 线段允许正常最小间距约束，也允许在强反转时豁免距离约束
8. 图表当前只画线段，不画分型箭头

这就是今天关于分型、包含、线段的最终统一口径。
