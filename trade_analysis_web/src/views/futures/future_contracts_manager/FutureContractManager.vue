<script lang="ts" setup>
import {
  createFutureContract,
  getFutureContractList,
  updateFutureContract,
  type FutureContract,
  type FutureContractCreateParams,
} from '@/api/modules'
import { formatDateTime as formatDateTimeByDayjs } from '@/utils/date'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

interface ContractForm {
  contract_id?: number
  symbol: string
  exchange: string
  name: string
}

const contracts = ref<FutureContract[]>([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const formRef = ref<FormInstance>()

const form = reactive<ContractForm>({
  symbol: '',
  exchange: '',
  name: '',
})

const rules = reactive<FormRules<ContractForm>>({
  symbol: [{ required: true, message: '请输入合约代码', trigger: 'blur' }],
  exchange: [{ required: true, message: '请输入交易所', trigger: 'blur' }],
  name: [{ required: true, message: '请输入合约名称', trigger: 'blur' }],
})

const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新增合约' : '修改合约'))

const resetForm = () => {
  form.contract_id = undefined
  form.symbol = ''
  form.exchange = ''
  form.name = ''
  formRef.value?.clearValidate()
}

const loadContracts = async () => {
  loading.value = true
  try {
    contracts.value = await getFutureContractList()
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

onMounted(() => {
  loadContracts()
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
      <el-table-column prop="symbol" label="合约代码" min-width="140" />
      <el-table-column prop="exchange" label="交易所" min-width="120" />
      <el-table-column prop="name" label="合约名称" min-width="180" />
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

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="460px" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="合约代码" prop="symbol">
          <el-input v-model.trim="form.symbol" placeholder="请输入合约代码" />
        </el-form-item>
        <el-form-item label="交易所" prop="exchange">
          <el-input v-model.trim="form.exchange" placeholder="请输入交易所" />
        </el-form-item>
        <el-form-item label="合约名称" prop="name">
          <el-input v-model.trim="form.name" placeholder="请输入合约名称" />
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
</style>
