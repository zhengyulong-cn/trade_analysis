<script lang="ts" setup>
import { createProduct, getProductList, updateProduct, type Product, type ProductCreateParams } from '@/api/modules'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { formatDateTime } from '@/utils/date'

interface ProductForm {
  product_id?: number
  product_code: string
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

const products = ref<Product[]>([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const formRef = ref<FormInstance>()

const form = reactive<ProductForm>({
  product_code: '',
  exchange: '',
  name: '',
})

const rules = reactive<FormRules<ProductForm>>({
  product_code: [{ required: true, message: '请输入品种代码', trigger: 'blur' }],
  exchange: [{ required: true, message: '请选择交易所', trigger: 'change' }],
  name: [{ required: true, message: '请输入品种名称', trigger: 'blur' }],
})

const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新增品种' : '编辑品种'))

const resetForm = () => {
  form.product_id = undefined
  form.product_code = ''
  form.exchange = ''
  form.name = ''
  formRef.value?.clearValidate()
}

const loadProducts = async () => {
  loading.value = true
  try {
    products.value = await getProductList()
  } catch {
    ElMessage.error('获取品种列表失败')
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  dialogMode.value = 'create'
  resetForm()
  dialogVisible.value = true
}

const openEditDialog = (row: Product) => {
  dialogMode.value = 'edit'
  form.product_id = row.product_id
  form.product_code = row.product_code
  form.exchange = row.exchange
  form.name = row.name
  dialogVisible.value = true
}

const submitForm = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) {
    return
  }
  submitting.value = true
  try {
    const payload: ProductCreateParams = {
      product_code: form.product_code.trim().toUpperCase(),
      exchange: form.exchange.trim().toUpperCase(),
      name: form.name.trim(),
    }
    if (dialogMode.value === 'create') {
      await createProduct(payload)
      ElMessage.success('品种创建成功')
    } else if (form.product_id) {
      await updateProduct({ product_id: form.product_id, ...payload })
      ElMessage.success('品种更新成功')
    }
    dialogVisible.value = false
    await loadProducts()
  } catch {
    ElMessage.error(dialogMode.value === 'create' ? '品种创建失败' : '品种更新失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  void loadProducts()
})
</script>

<template>
  <div class="pageBox product-manager">
    <div class="toolbar">
      <div>
        <h2 class="title">品种管理</h2>
        <p class="subtitle">先维护品种，再把多个具体合约归属到对应品种下。</p>
      </div>
      <el-button type="primary" @click="openCreateDialog">新增品种</el-button>
    </div>

    <el-table v-loading="loading" :data="products" border row-key="product_id" empty-text="暂无品种">
      <el-table-column prop="product_id" label="ID" width="90" />
      <el-table-column prop="product_code" label="品种代码" min-width="140" />
      <el-table-column prop="exchange" label="交易所" width="120" />
      <el-table-column prop="name" label="品种名称" min-width="180" />
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

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="32rem" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="7rem">
        <el-form-item label="品种代码" prop="product_code">
          <el-input v-model.trim="form.product_code" placeholder="例如 RB、MA、EG" />
        </el-form-item>
        <el-form-item label="交易所" prop="exchange">
          <el-select v-model="form.exchange" style="width: 100%" placeholder="请选择交易所">
            <el-option v-for="option in exchangeOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="品种名称" prop="name">
          <el-input v-model.trim="form.name" placeholder="例如 螺纹钢、甲醇、乙二醇" />
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
.product-manager {
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
</style>
