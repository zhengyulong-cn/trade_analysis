<script lang="ts" setup>
</script>

<template>
  <div class="pageBox home-page">
    <div class="center-box">
      <section class="section-box">
        <div class="title">开仓检查</div>
        <el-popover trigger="hover" placement="bottom-end" width="60vw">
          <template #reference>
            <p class="content">①30F段类型及交易视角</p>
          </template>
          <template #default>
            <el-image src="/assets/images/操作视角的确定.svg" fit="fill" />
          </template>
        </el-popover>
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
              <p>区间边界附近+两次以上尝试突破受阻不符合开仓信号</p>
            </div>
          </template>
        </el-popover>
        <p>③设置的止损位能否接受？</p>
      </section>
      <section class="section-box">
        <div class="title">操作警醒</div>
        <div>①不要做垃圾机会，交易系统外似是而非的机会都不要操作！</div>
        <div>②不要随随便便拉止损，更不能删除止损！</div>
        <div>③回撤时候看持仓方向是否受到阻力，没有受阻就是普通回调而已</div>
      </section>
    </div>
    <el-image class="page-el-image" src="/assets/images/remind.png" fit="fill" />
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
.center-box {
  position: fixed;
  background-color: rgba(161, 17, 161, 0.4);
  color: white;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 100;
  padding: 1rem;
  border-radius: .5rem;
  font-size: 1.5rem;
  .section-box {
    .title {
      font-size: 2rem;
    }
    .content {
      width: fit-content;
    }
  }
}
</style>
