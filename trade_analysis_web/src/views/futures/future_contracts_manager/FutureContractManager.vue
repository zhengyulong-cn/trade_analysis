<script lang="ts" setup>
import {
  createFutureContract,
  getFutureContractList,
  updateFutureContract,
  type FutureContract,
  type FutureContractCreateParams,
} from '@/api/modules'
import { Star, StarFilled } from '@element-plus/icons-vue'
import { formatDateTime as formatDateTimeByDayjs } from '@/utils/date'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

interface ContractForm {
  contract_id?: number
  symbol: string
  exchange: string
  name: string
  auto_load_segments: number
}

const exchangeOptions = [
  { label: '中国金融期货交易所-CFFEX', value: 'CFFEX' },
  { label: '上海期货交易所-SHFE', value: 'SHFE' },
  { label: '上海国际能源交易中心-INE', value: 'INE' },
  { label: '郑州商品交易所-CZCE', value: 'CZCE' },
  { label: '大连商品交易所-DCE', value: 'DCE' },
  { label: '广州期货交易所-GFEX', value: 'GFEX' },
] as const

const contracts = ref<FutureContract[]>([])
const loading = ref(false)
const submitting = ref(false)
const favoriteTogglingIds = ref<number[]>([])
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const formRef = ref<FormInstance>()

const form = reactive<ContractForm>({
  symbol: '',
  exchange: '',
  name: '',
  auto_load_segments: 1,
})

const rules = reactive<FormRules<ContractForm>>({
  symbol: [{ required: true, message: '请输入合约代码', trigger: 'blur' }],
  exchange: [{ required: true, message: '请选择交易所', trigger: 'change' }],
  name: [{ required: true, message: '请输入合约名称', trigger: 'blur' }],
})

const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新增合约' : '修改合约'))

const sortContractsBySymbol = (items: FutureContract[]) => {
  return [...items].sort((first, second) => {
    return first.symbol.localeCompare(second.symbol, 'zh-CN')
  })
}

const resetForm = () => {
  form.contract_id = undefined
  form.symbol = ''
  form.exchange = ''
  form.name = ''
  form.auto_load_segments = 1
  formRef.value?.clearValidate()
}

const loadContracts = async () => {
  loading.value = true
  try {
    const response = await getFutureContractList()
    contracts.value = sortContractsBySymbol(response)
  } catch {
    ElMessage.error('获取期货合约列表失败')
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  dialogMode.value = 'create'
  resetForm()
  dialogVisible.value = true
}

const openEditDialog = (row: FutureContract) => {
  dialogMode.value = 'edit'
  form.contract_id = row.contract_id
  form.symbol = row.symbol
  form.exchange = row.exchange
  form.name = row.name
  form.auto_load_segments = row.auto_load_segments
  formRef.value?.clearValidate()
  dialogVisible.value = true
}

const submitForm = async () => {
  if (!formRef.value) {
    return
  }

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }

  submitting.value = true
  try {
    const payload: FutureContractCreateParams = {
      symbol: form.symbol.trim(),
      exchange: form.exchange.trim(),
      name: form.name.trim(),
      auto_load_segments: form.auto_load_segments,
    }

    if (dialogMode.value === 'create') {
      await createFutureContract(payload)
      ElMessage.success('创建合约成功')
    } else if (form.contract_id) {
      await updateFutureContract({
        contract_id: form.contract_id,
        ...payload,
      })
      ElMessage.success('修改合约成功')
    }

    dialogVisible.value = false
    await loadContracts()
  } catch {
    ElMessage.error(dialogMode.value === 'create' ? '创建合约失败' : '修改合约失败')
  } finally {
    submitting.value = false
  }
}

const formatDateTime = (_row: FutureContract, _column: unknown, value: string) => {
  return formatDateTimeByDayjs(value)
}

const formatAutoLoadSegments = (value: number) => {
  return value === 1 ? '自动载入' : '手动载入'
}

const isFavoriteToggling = (contractId: number) => {
  return favoriteTogglingIds.value.includes(contractId)
}

const handleFavoriteToggle = async (row: FutureContract) => {
  favoriteTogglingIds.value = [...favoriteTogglingIds.value, row.contract_id]

  try {
    const updatedContract = await updateFutureContract({
      contract_id: row.contract_id,
      is_favorite: row.is_favorite === 1 ? 0 : 1,
    })
    contracts.value = sortContractsBySymbol(
      contracts.value.map((item) => {
        return item.contract_id === updatedContract.contract_id ? updatedContract : item
      }),
    )
    ElMessage.success(updatedContract.is_favorite === 1 ? '已加入收藏' : '已取消收藏')
  } catch {
    ElMessage.error('切换合约收藏状态失败')
  } finally {
    favoriteTogglingIds.value = favoriteTogglingIds.value.filter((item) => item !== row.contract_id)
  }
}

onMounted(() => {
  void loadContracts()
})
</script>

<template>
  <div class="pageBox contract-manager">
    <div class="toolbar">
      <div>
        <h2 class="title">期货合约管理</h2>
        <p class="subtitle">维护期货合约基础信息</p>
      </div>
      <el-button type="primary" @click="openCreateDialog">新增合约</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="contracts"
      border
      row-key="contract_id"
      empty-text="暂无期货合约"
    >
      <el-table-column prop="contract_id" label="ID" width="90" />
      <el-table-column prop="symbol" label="合约代码" min-width="160">
        <template #default="{ row }">
          <div class="symbol-cell">
            <span class="symbol-text">{{ row.symbol }}</span>
            <button
              type="button"
              class="favorite-button"
              :class="{ 'favorite-button--active': row.is_favorite === 1 }"
              :disabled="isFavoriteToggling(row.contract_id)"
              @click="handleFavoriteToggle(row)"
            >
              <el-icon>
                <StarFilled v-if="row.is_favorite === 1" />
                <Star v-else />
              </el-icon>
            </button>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="exchange" label="交易所" min-width="120" />
      <el-table-column prop="name" label="合约名称" min-width="180" />
      <el-table-column prop="auto_load_segments" label="线段载入方式" min-width="120">
        <template #default="{ row }">
          <el-tag :type="row.auto_load_segments === 1 ? 'success' : 'info'">
            {{ formatAutoLoadSegments(row.auto_load_segments) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column
        prop="create_at"
        label="创建时间"
        min-width="180"
        :formatter="formatDateTime"
      />
      <el-table-column
        prop="updated_at"
        label="更新时间"
        min-width="180"
        :formatter="formatDateTime"
      />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="openEditDialog(row)">修改</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="32rem" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="8rem">
        <el-form-item label="合约代码" prop="symbol">
          <el-input v-model.trim="form.symbol" placeholder="请输入合约代码" />
        </el-form-item>
        <el-form-item label="交易所" prop="exchange">
          <el-select v-model="form.exchange" placeholder="请选择交易所" style="width: 100%">
            <el-option
              v-for="option in exchangeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="合约名称" prop="name">
          <el-input v-model.trim="form.name" placeholder="请输入合约名称" />
        </el-form-item>
        <el-form-item label="线段载入方式" prop="auto_load_segments">
          <el-switch
            v-model="form.auto_load_segments"
            :active-value="1"
            :inactive-value="0"
            active-text="自动"
            inactive-text="手动"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="less" scoped>
.contract-manager {
  padding: 16px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.subtitle {
  margin: 6px 0 0;
  color: #909399;
  font-size: 13px;
}

.symbol-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.symbol-text {
  font-weight: 600;
  color: #303133;
}

.favorite-button {
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #c0c4cc;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition:
    color 0.2s ease,
    background-color 0.2s ease;
}

.favorite-button:hover:not(:disabled) {
  color: #e6a23c;
  background: rgba(230, 162, 60, 0.1);
}

.favorite-button:disabled {
  cursor: not-allowed;
  opacity: 0.68;
}

.favorite-button--active {
  color: #e6a23c;
}
</style>
