<script lang="ts" setup>
import {
  createFutureContract,
  getFutureContractList,
  getProductList,
  updateFutureContract,
  type FutureContract,
  type FutureContractCreateParams,
  type Product,
} from '@/api/modules'
import { Star, StarFilled } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { formatDateTime } from '@/utils/date'

interface ContractForm {
  contract_id?: number
  product_id?: number
  symbol: string
  exchange: string
  name: string
}

const exchangeOptions = [
  { label: 'CFFEX', value: 'CFFEX' },
  { label: 'SHFE', value: 'SHFE' },
  { label: 'INE', value: 'INE' },
  { label: 'CZCE', value: 'CZCE' },
  { label: 'DCE', value: 'DCE' },
  { label: 'GFEX', value: 'GFEX' },
] as const

const contracts = ref<FutureContract[]>([])
const products = ref<Product[]>([])
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
})

const rules = reactive<FormRules<ContractForm>>({
  product_id: [{ required: true, message: '请选择归属品种', trigger: 'change' }],
  symbol: [{ required: true, message: '请输入合约代码', trigger: 'blur' }],
  exchange: [{ required: true, message: '请选择交易所', trigger: 'change' }],
  name: [{ required: true, message: '请输入合约名称', trigger: 'blur' }],
})

const productOptions = computed(() =>
  products.value.map((item) => ({
    label: `${item.product_code} ${item.name} (${item.exchange})`,
    value: item.product_id,
  })),
)

const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新增合约' : '编辑合约'))

const sortContracts = (items: FutureContract[]) =>
  [...items].sort((first, second) => first.symbol.localeCompare(second.symbol, 'zh-CN'))

const resetForm = () => {
  form.contract_id = undefined
  form.product_id = undefined
  form.symbol = ''
  form.exchange = ''
  form.name = ''
  formRef.value?.clearValidate()
}

const loadData = async () => {
  loading.value = true
  try {
    const [contractData, productData] = await Promise.all([
      getFutureContractList(),
      getProductList(),
    ])
    contracts.value = sortContracts(contractData)
    products.value = productData
  } catch {
    ElMessage.error('获取合约或品种列表失败')
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
  form.product_id = row.product_id
  form.symbol = row.symbol
  form.exchange = row.exchange
  form.name = row.name
  dialogVisible.value = true
}

const submitForm = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid || !form.product_id) {
    return
  }

  submitting.value = true
  try {
    const payload: FutureContractCreateParams = {
      product_id: form.product_id,
      symbol: form.symbol.trim(),
      exchange: form.exchange.trim(),
      name: form.name.trim(),
    }

    if (dialogMode.value === 'create') {
      await createFutureContract(payload)
      ElMessage.success('合约创建成功')
    } else if (form.contract_id) {
      await updateFutureContract({ contract_id: form.contract_id, ...payload })
      ElMessage.success('合约更新成功')
    }

    dialogVisible.value = false
    await loadData()
  } catch {
    ElMessage.error(dialogMode.value === 'create' ? '合约创建失败' : '合约更新失败')
  } finally {
    submitting.value = false
  }
}

const isFavoriteToggling = (contractId: number) => favoriteTogglingIds.value.includes(contractId)

const handleFavoriteToggle = async (row: FutureContract) => {
  favoriteTogglingIds.value = [...favoriteTogglingIds.value, row.contract_id]
  try {
    const updatedContract = await updateFutureContract({
      contract_id: row.contract_id,
      is_favorite: row.is_favorite === 1 ? 0 : 1,
    })
    contracts.value = sortContracts(
      contracts.value.map((item) => (item.contract_id === updatedContract.contract_id ? updatedContract : item)),
    )
    ElMessage.success(updatedContract.is_favorite === 1 ? '已加入收藏' : '已取消收藏')
  } catch {
    ElMessage.error('切换收藏状态失败')
  } finally {
    favoriteTogglingIds.value = favoriteTogglingIds.value.filter((item) => item !== row.contract_id)
  }
}

onMounted(() => {
  void loadData()
})
</script>

<template>
  <div class="pageBox contract-manager">
    <div class="toolbar">
      <div>
        <h2 class="title">期货合约管理</h2>
        <p class="subtitle">一个品种下可以挂多个合约，这里维护具体可交易合约。</p>
      </div>
      <el-button type="primary" @click="openCreateDialog">新增合约</el-button>
    </div>

    <el-table v-loading="loading" :data="contracts" border row-key="contract_id" empty-text="暂无合约">
      <el-table-column prop="contract_id" label="ID" width="90" />
      <el-table-column label="归属品种" min-width="180">
        <template #default="{ row }">
          {{ row.product_code || '-' }} {{ row.product_name || '' }}
        </template>
      </el-table-column>
      <el-table-column prop="symbol" label="合约代码" min-width="140">
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
      <el-table-column prop="exchange" label="交易所" width="120" />
      <el-table-column prop="name" label="合约名称" min-width="180" />
      <el-table-column label="更新时间" min-width="180">
        <template #default="{ row }">
          {{ formatDateTime(row.updated_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="openEditDialog(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="34rem" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="7rem">
        <el-form-item label="归属品种" prop="product_id">
          <el-select v-model="form.product_id" style="width: 100%" filterable placeholder="请选择品种">
            <el-option v-for="item in productOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="合约代码" prop="symbol">
          <el-input v-model.trim="form.symbol" placeholder="例如 RB2410、MA2501" />
        </el-form-item>
        <el-form-item label="交易所" prop="exchange">
          <el-select v-model="form.exchange" style="width: 100%" placeholder="请选择交易所">
            <el-option v-for="option in exchangeOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="合约名称" prop="name">
          <el-input v-model.trim="form.name" placeholder="例如 螺纹钢2410、甲醇2501" />
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
  gap: 16px;
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
}
.favorite-button {
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #c0c4cc;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.favorite-button--active {
  color: #e6a23c;
}
</style>
