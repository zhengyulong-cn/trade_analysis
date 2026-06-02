<script lang="ts" setup>
const tradePatternDisplayList = [
  {
    title: '趋势推动段',
    subText: '开仓信号：EMA20阻力+对基准位反向突破',
    urlList: [
      "/assets/images/trade_pattern/模式一例子.png"
    ]
  },
  {
    title: '趋势回调段',
    subText: '开仓信号：EMA120阻力+反转结构',
    urlList: [
      "/assets/images/trade_pattern/模式二例子1.png",
      "/assets/images/trade_pattern/模式二例子2.png",
    ]
  },
  {
    title: '区间内部段或（假突破）趋势回调段转区间内部段',
    subText: '开仓信号：区间上下轨附近+两次以上尝试突破受阻',
    urlList: [
      "/assets/images/trade_pattern/模式三例子.png"
    ]
  },
  {
    title: '（真突破）区间内部段转趋势推动段',
    subText: '开仓信号：阻力位附近+受阻失败出现K线反包',
    urlList: [
      "/assets/images/trade_pattern/模式四例子.png"
    ]
  }
]
</script>

<template>
  <div class="pageBox home-page">
    <header class="header-box">
      <div class="left-box">
        <section class="section-box">
          <div class="title">开仓检查</div>
          <p class="content">①30F段类型及交易视角</p>
          <el-popover trigger="hover" placement="bottom-start" width="fit-content">
            <template #reference>
              <p class="content">②开仓信号类型</p>
            </template>
            <template #default>
              <div>
                <p>EMA20阻力+站稳关键位</p>
                <p>EMA120阻力+头肩顶/头肩底</p>
                <p>EMA120阻力+三推楔形</p>
                <p>EMA120阻力+突破交易区间然后回拉</p>
                <p>区间边界附近+两次以上尝试突破受阻</p>
                <p>区间边界附近+受阻失败K线反包</p>
              </div>
            </template>
          </el-popover>
          <p>③是否有同板块其他品种买点共振？</p>
          <p>④设置的止损位能否接受？</p>
        </section>
        <section class="section-box">
          <div class="title">持仓</div>
          <div>①已较大幅度盈利单子拉止损超过成本线，<span class="highlight">浮盈就不能转化为亏损。</span></div>
          <div>②回撤时候看持仓方向是否受到阻力，没有受阻就是普通回调而已。</div>
          <!-- <div>②<span class="highlight">不要拉硬止损</span>，更不能删除止损！亏损不要有侥幸念想扛单！</div> -->
          <!-- <div>③回撤时候看持仓方向是否受到阻力，没有受阻就是普通回调而已</div> -->
        </section>
        <section class="section-box">
          <div class="title">操作红线</div>
          <div>①<span class="highlight">不要让硬止损扩大</span>，更不能删除止损！亏损不要有侥幸念想扛单！</div>
          <div>②如果今天做的不顺，就休息吧！</div>
        </section>
      </div>
      <div class="right-box">
        <el-image src="/assets/images/操作视角的确定.svg" fit="contain" />
      </div>
    </header>
    <div class="trade-pattern-display">
      <div class="trade-pattern-item" v-for="tradePatternDisplayItem in tradePatternDisplayList">
        <header>
          <div class="title">{{ tradePatternDisplayItem.title }}</div>
          <div class="sub-text">{{ tradePatternDisplayItem.subText }}</div>
        </header>
        <el-carousel indicator-position="none" height="29rem">
          <el-carousel-item v-for="url in tradePatternDisplayItem.urlList" :key="url">
            <el-image :src="url" fit="contain" />
          </el-carousel-item>
        </el-carousel>
      </div>
    </div>
  </div>
</template>

<style lang="less" scoped>
.home-page {
  min-height: calc(100vh - 4rem);
}
.page-el-image {
  width: 100%;
  height: 100%;
}
.header-box {
  margin: .5rem;
  display: flex;
  flex-direction: row;
  column-gap: .5rem;
  .left-box {
    background-color: rgba(161, 17, 161, 0.4);
    color: white;
    padding: 1rem;
    border-radius: .5rem;
    font-size: 1.5rem;
    font-family: 'kaiti';
    .section-box {
      .title {
        font-size: 2rem;
        font-weight: bolder;
        color: yellow;
        text-decoration-line: underline;
      }
      .content {
        width: fit-content;
      }
      .highlight {
        color: red;
        font-weight: bolder;
      }
    }
  }
}
.trade-pattern-display {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: .5rem;
  margin: .5rem;
  .trade-pattern-item {
    background-color: rgba(255, 255, 255, 0.9);
    border: 1px solid #e2e2e3;
    border-radius: .5rem;
    header {
      background-color: #f6f6f7;
      padding: .5rem;
      border-top-left-radius: .5rem;
      border-top-right-radius: .5rem;
      .title {
        font-weight: bold;
      }
      .sub-text {
        font-size: .75rem;
        color: #67676c;
      }
    }
    :el-image {
      display: block;
      width: 100%;
      height: 100%;
    }
  }
}
</style>
