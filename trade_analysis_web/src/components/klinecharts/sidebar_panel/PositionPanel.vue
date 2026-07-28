<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import type { FutureContract } from '@/api/modules'
import { usePositionOverlayStore, type PositionDirection } from '@/stores/positionOverlays'

const props = withDefaults(defineProps<{
  contracts: FutureContract[]
  selectedContract?: string
  latestPrice?: number
}>(), { selectedContract: '', latestPrice: undefined })

const emit = defineEmits<{ 'update:selectedContract': [value: string] }>()
const positionStore = usePositionOverlayStore()
const dialogVisible = ref(false)
const editingPositionId = ref<string>()
const form = ref({
  symbol: '',
  direction: 'long' as PositionDirection,
  openPrice: undefined as number | undefined,
  quantity: 1,
  openTime: '',
  note: '',
})

const sortedPositions = computed(() => [...positionStore.positions].sort((first, second) => second.openTime.localeCompare(first.openTime)))

const padTimePart = (value: number) => String(value).padStart(2, '0')

const getLocalDateTimeValue = () => {
  const now = new Date()
  return `${now.getFullYear()}-${padTimePart(now.getMonth() + 1)}-${padTimePart(now.getDate())}T${padTimePart(now.getHours())}:${padTimePart(now.getMinutes())}`
}

const openCreateDialog = () => {
  editingPositionId.value = undefined
  form.value = {
    symbol: props.selectedContract,
    direction: 'long',
    openPrice: Number.isFinite(props.latestPrice) ? props.latestPrice : undefined,
    quantity: 1,
    openTime: getLocalDateTimeValue(),
    note: '',
  }
  dialogVisible.value = true
}

const openEditDialog = (positionId: string) => {
  const position = positionStore.positions.find((item) => item.id === positionId)
  if (!position) return
  editingPositionId.value = position.id
  form.value = {
    symbol: position.symbol,
    direction: position.direction,
    openPrice: position.openPrice,
    quantity: position.quantity,
    openTime: position.openTime,
    note: position.note,
  }
  dialogVisible.value = true
}

const deletePosition = async (positionId: string) => {
  try {
    await ElMessageBox.confirm('删除后无法恢复，确定删除这条盘中持仓吗？', '删除持仓', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    positionStore.closePosition(positionId)
  } catch {}
}

const savePosition = () => {
  const { symbol, direction, openPrice, quantity, openTime, note } = form.value
  if (!symbol || !Number.isFinite(openPrice) || !openPrice || !Number.isFinite(quantity) || quantity <= 0 || !openTime) {
    return
  }
  const position = { symbol, direction, openPrice, quantity, openTime, note: note.trim() }
  if (editingPositionId.value) {
    positionStore.updatePosition(editingPositionId.value, position)
  } else {
    positionStore.addPosition(position)
  }
  dialogVisible.value = false
}
</script>

<template>
  <section class="position-panel">
    <header class="panel-header">
      <span>持仓</span>
      <el-button type="primary" size="small" @click="openCreateDialog">新增</el-button>
    </header>
    <el-scrollbar class="position-scrollbar" height="45rem">
      <div v-if="!sortedPositions.length" class="panel-empty">暂无盘中持仓</div>
      <article v-for="position in sortedPositions" :key="position.id" class="position-item" @click="emit('update:selectedContract', position.symbol)">
        <div class="position-topline">
          <strong>{{ position.symbol }}</strong>
          <span :class="position.direction === 'long' ? 'direction-long' : 'direction-short'">{{ position.direction === 'long' ? '多' : '空' }}</span>
          <div class="position-actions">
            <el-button link type="primary" size="small" @click.stop="openEditDialog(position.id)">编辑</el-button>
            <el-button link type="danger" size="small" @click.stop="deletePosition(position.id)">删除</el-button>
            <el-button link type="danger" size="small" @click.stop="positionStore.closePosition(position.id)">平仓</el-button>
          </div>
        </div>
        <div class="position-detail">{{ position.quantity }} 手 · {{ position.openPrice }}</div>
        <div class="position-detail">{{ position.openTime.replace('T', ' ') }}</div>
      </article>
    </el-scrollbar>
  </section>
  <el-dialog v-model="dialogVisible" :title="editingPositionId ? '编辑盘中持仓' : '新增盘中持仓'" width="24rem">
    <el-form label-width="5rem">
      <el-form-item label="品种"><el-select v-model="form.symbol" filterable><el-option v-for="contract in contracts" :key="contract.contract_id" :label="`${contract.symbol} ${contract.name}`" :value="contract.symbol" /></el-select></el-form-item>
      <el-form-item label="方向"><el-radio-group v-model="form.direction"><el-radio-button value="long">多</el-radio-button><el-radio-button value="short">空</el-radio-button></el-radio-group></el-form-item>
      <el-form-item label="开仓价"><el-input-number v-model="form.openPrice" :min="0" :precision="1" /></el-form-item>
      <el-form-item label="手数"><el-input-number v-model="form.quantity" :min="1" :precision="0" /></el-form-item>
      <el-form-item label="开仓时间"><el-date-picker v-model="form.openTime" type="datetime" value-format="YYYY-MM-DDTHH:mm" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="form.note" /></el-form-item>
    </el-form>
    <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="savePosition">保存</el-button></template>
  </el-dialog>
</template>

<style scoped lang="less">
.position-panel { width: 18rem; height: 100%; display: flex; flex-direction: column; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; }
.panel-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; border-bottom: 1px solid #e2e8f0; font-weight: 600; }
.position-scrollbar { flex: 1; }.panel-empty { padding: 24px 12px; color: #94a3b8; text-align: center; }
.position-item { padding: 10px; border-bottom: 1px solid #f1f5f9; cursor: pointer; }.position-item:hover { background: #f8fafc; }
.position-topline { display: flex; align-items: center; gap: 8px; }.position-actions { display: flex; gap: 4px; margin-left: auto; }.direction-long { color: #dc2626; }.direction-short { color: #2563eb; }.position-detail { margin-top: 4px; color: #64748b; font-size: 12px; }
</style>
