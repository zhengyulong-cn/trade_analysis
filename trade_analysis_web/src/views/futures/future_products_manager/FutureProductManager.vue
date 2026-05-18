<script lang="ts" setup>
import {
  createFutureProduct,
  getFutureProductList,
  updateFutureProduct,
  type FutureProduct,
  type FutureProductCreateParams,
} from '@/api/modules'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { formatDateTime as formatDateTimeByDayjs } from '@/utils/date'

interface ProductForm {
  product_id?: number
  product_code: string
  display_name: string
  alias_names_text: string
}

const products = ref<FutureProduct[]>([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const formRef = ref<FormInstance>()

const form = reactive<ProductForm>({
  product_code: '',
  display_name: '',
  alias_names_text: '',
})

const rules = reactive<FormRules<ProductForm>>({
  product_code: [{ required: true, message: '请输入品种代码', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入主名称', trigger: 'blur' }],
})

const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新增品种' : '修改品种'))

const sortProducts = (items: FutureProduct[]) => {
  return [...items].sort((first, second) => {
    return first.product_code.localeCompare(second.product_code, 'zh-CN')
  })
}

const resetForm = () => {
  form.product_id = undefined
  form.product_code = ''
  form.display_name = ''
  form.alias_names_text = ''
  formRef.value?.clearValidate()
}

const loadProducts = async () => {
  loading.value = true
  try {
    const response = await getFutureProductList()
    products.value = sortProducts(response)
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

const openEditDialog = (row: FutureProduct) => {
  dialogMode.value = 'edit'
  form.product_id = row.product_id
  form.product_code = row.product_code
  form.display_name = row.display_name
  form.alias_names_text = row.alias_names.join('，')
  formRef.value?.clearValidate()
  dialogVisible.value = true
}

const parseAliasNames = (rawValue: string) => {
  return rawValue
    .split(/[\n,，、;]/)
    .map((item) => item.trim())
    .filter(Boolean)
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
    const payload: FutureProductCreateParams = {
      product_code: form.product_code.trim().toUpperCase(),
      display_name: form.display_name.trim(),
      alias_names: parseAliasNames(form.alias_names_text),
    }

    if (dialogMode.value === 'create') {
      await createFutureProduct(payload)
      ElMessage.success('创建品种成功')
    } else if (form.product_id) {
      await updateFutureProduct({
        product_id: form.product_id,
        ...payload,
      })
      ElMessage.success('修改品种成功')
    }

    dialogVisible.value = false
    await loadProducts()
  } catch {
    ElMessage.error(dialogMode.value === 'create' ? '创建品种失败' : '修改品种失败')
  } finally {
    submitting.value = false
  }
}

const formatDateTime = (_row: FutureProduct, _column: unknown, value: string) => {
  return formatDateTimeByDayjs(value)
}

onMounted(() => {
  void loadProducts()
})
</script>

<template>
  <div class="pageBox future-product-manager">
    <div class="toolbar">
      <div>
        <h2 class="title">期货品种管理</h2>
        <p class="subtitle">维护期货品种基础信息，后续AI画像和研报阅读都基于品种展开。</p>
      </div>
      <el-button type="primary" @click="openCreateDialog">新增品种</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="products"
      border
      row-key="product_id"
      empty-text="暂无期货品种"
    >
      <el-table-column prop="product_id" label="ID" width="90" />
      <el-table-column prop="product_code" label="品种代码" min-width="140" />
      <el-table-column prop="display_name" label="主名称" min-width="180" />
      <el-table-column label="别名" min-width="220">
        <template #default="{ row }">
          {{ row.alias_names.length ? row.alias_names.join('、') : '-' }}
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
        <el-form-item label="品种代码" prop="product_code">
          <el-input v-model.trim="form.product_code" placeholder="请输入品种代码，如 RB、MA、EG" />
        </el-form-item>
        <el-form-item label="主名称" prop="display_name">
          <el-input v-model.trim="form.display_name" placeholder="请输入主名称，如 乙二醇" />
        </el-form-item>
        <el-form-item label="别名">
          <el-input
            v-model="form.alias_names_text"
            type="textarea"
            :rows="3"
            placeholder="请输入别名，支持逗号、顿号或换行分隔，如 甘醇、MEG"
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
.future-product-manager {
  padding: 16px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  gap: 16px;
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

@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
