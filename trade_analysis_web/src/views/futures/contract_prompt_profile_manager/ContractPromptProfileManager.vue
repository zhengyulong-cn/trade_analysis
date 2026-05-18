<script lang="ts" setup>
import {
  createProductPromptProfile,
  deleteProductPromptProfile,
  getProductList,
  getProductPromptProfileList,
  updateProductPromptProfile,
  type Product,
  type ProductPromptProfile,
} from '@/api/modules'
import { Delete, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { formatDateTime } from '@/utils/date'

interface PromptProfileForm {
  profile_id?: number
  product_id?: number
  focus_dimensions_text: string
  analysis_style: string
  extra_instruction: string
  output_preference: string
  is_active: boolean
}

const products = ref<Product[]>([])
const promptProfiles = ref<ProductPromptProfile[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const deleting = ref(false)
const keyword = ref('')
const formRef = ref<FormInstance>()
const selectedProduct = ref<Product | null>(null)

const form = reactive<PromptProfileForm>({
  focus_dimensions_text: '',
  analysis_style: '',
  extra_instruction: '',
  output_preference: '',
  is_active: true,
})

const rules = reactive<FormRules<PromptProfileForm>>({
  focus_dimensions_text: [{ required: true, message: '请输入关注维度', trigger: 'blur' }],
})

const profileMap = computed(() => new Map(promptProfiles.value.map((item) => [item.product_id, item])))

const rows = computed(() => {
  const normalizedKeyword = keyword.value.trim().toLowerCase()
  return products.value
    .map((product) => ({
      ...product,
      promptProfile: profileMap.value.get(product.product_id) ?? null,
    }))
    .filter((item) => {
      if (!normalizedKeyword) {
        return true
      }
      return (
        item.product_code.toLowerCase().includes(normalizedKeyword) ||
        item.name.toLowerCase().includes(normalizedKeyword) ||
        item.exchange.toLowerCase().includes(normalizedKeyword)
      )
    })
})

const dialogTitle = computed(() => {
  if (!selectedProduct.value) {
    return 'AI画像配置'
  }
  return `AI画像配置 - ${selectedProduct.value.product_code} ${selectedProduct.value.name}`
})

const loadData = async () => {
  loading.value = true
  try {
    const [productData, profileData] = await Promise.all([
      getProductList(),
      getProductPromptProfileList(),
    ])
    products.value = productData
    promptProfiles.value = profileData
  } catch {
    ElMessage.error('获取品种或AI画像列表失败')
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.profile_id = undefined
  form.product_id = undefined
  form.focus_dimensions_text = ''
  form.analysis_style = ''
  form.extra_instruction = ''
  form.output_preference = ''
  form.is_active = true
  selectedProduct.value = null
  formRef.value?.clearValidate()
}

const parseFocusDimensions = (rawValue: string) => {
  return rawValue
    .split(/[\n,，、;]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

const openDialog = (product: Product) => {
  resetForm()
  selectedProduct.value = product

  const profile = profileMap.value.get(product.product_id)
  if (profile) {
    form.profile_id = profile.profile_id
    form.product_id = profile.product_id
    form.focus_dimensions_text = profile.focus_dimensions.join('，')
    form.analysis_style = profile.analysis_style ?? ''
    form.extra_instruction = profile.extra_instruction ?? ''
    form.output_preference = profile.output_preference ?? ''
    form.is_active = profile.is_active === 1
  } else {
    form.product_id = product.product_id
  }

  dialogVisible.value = true
}

const submitForm = async () => {
  if (!formRef.value || !selectedProduct.value) {
    return
  }
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }

  submitting.value = true
  try {
    const payload = {
      product_id: selectedProduct.value.product_id,
      focus_dimensions: parseFocusDimensions(form.focus_dimensions_text),
      analysis_style: form.analysis_style,
      extra_instruction: form.extra_instruction,
      output_preference: form.output_preference,
      is_active: form.is_active ? 1 : 0,
    }

    if (form.profile_id) {
      const updatedProfile = await updateProductPromptProfile({
        profile_id: form.profile_id,
        focus_dimensions: payload.focus_dimensions,
        analysis_style: payload.analysis_style,
        extra_instruction: payload.extra_instruction,
        output_preference: payload.output_preference,
        is_active: payload.is_active,
      })
      promptProfiles.value = promptProfiles.value.map((item) =>
        item.profile_id === updatedProfile.profile_id ? updatedProfile : item,
      )
      ElMessage.success('AI画像更新成功')
    } else {
      const createdProfile = await createProductPromptProfile(payload)
      promptProfiles.value = [...promptProfiles.value, createdProfile]
      ElMessage.success('AI画像保存成功')
    }

    dialogVisible.value = false
  } catch {
    ElMessage.error(form.profile_id ? 'AI画像更新失败' : 'AI画像保存失败')
  } finally {
    submitting.value = false
  }
}

const handleDelete = async () => {
  if (!form.profile_id) {
    return
  }
  try {
    await ElMessageBox.confirm('删除后将清空该品种的 AI画像配置，是否继续？', '删除AI画像', { type: 'warning' })
  } catch {
    return
  }

  deleting.value = true
  try {
    await deleteProductPromptProfile(form.profile_id)
    promptProfiles.value = promptProfiles.value.filter((item) => item.profile_id !== form.profile_id)
    dialogVisible.value = false
    ElMessage.success('AI画像删除成功')
  } catch {
    ElMessage.error('AI画像删除失败')
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  void loadData()
})
</script>

<template>
  <div class="pageBox profile-manager">
    <div class="toolbar">
      <div>
        <h2 class="title">AI画像配置</h2>
        <p class="subtitle">按品种维护分析画像，同一品种下的多个合约共用一套画像。</p>
      </div>
      <el-input
        v-model.trim="keyword"
        class="search-input"
        placeholder="搜索品种代码、名称、交易所"
        :prefix-icon="Search"
        clearable
      />
    </div>

    <el-table v-loading="loading" :data="rows" border row-key="product_id" empty-text="暂无品种数据">
      <el-table-column prop="product_code" label="品种代码" min-width="120" />
      <el-table-column prop="name" label="品种名称" min-width="180" />
      <el-table-column prop="exchange" label="交易所" width="120" />
      <el-table-column label="画像状态" width="120">
        <template #default="{ row }">
          <el-tag :type="row.promptProfile ? 'success' : 'info'" effect="plain">
            {{ row.promptProfile ? '已配置' : '未配置' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="关注维度" min-width="260">
        <template #default="{ row }">
          <div v-if="row.promptProfile?.focus_dimensions.length" class="dimension-list">
            <el-tag v-for="dimension in row.promptProfile.focus_dimensions" :key="dimension" size="small" effect="plain">
              {{ dimension }}
            </el-tag>
          </div>
          <span v-else class="placeholder-text">尚未配置</span>
        </template>
      </el-table-column>
      <el-table-column label="是否启用" width="120">
        <template #default="{ row }">
          <span v-if="row.promptProfile">{{ row.promptProfile.is_active === 1 ? '启用' : '停用' }}</span>
          <span v-else class="placeholder-text">未配置</span>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" min-width="180">
        <template #default="{ row }">
          {{ row.promptProfile ? formatDateTime(row.promptProfile.updated_at) : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="openDialog(row)">
            {{ row.promptProfile ? '编辑画像' : '新建画像' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="44rem" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="8rem">
        <el-form-item label="关注维度" prop="focus_dimensions_text">
          <el-input v-model="form.focus_dimensions_text" type="textarea" :rows="3" placeholder="例如：供给、需求、库存、基差、利润、政策" />
        </el-form-item>
        <el-form-item label="分析风格">
          <el-input v-model="form.analysis_style" type="textarea" :rows="2" placeholder="例如：偏基本面，中短期交易视角，先结论后原因" />
        </el-form-item>
        <el-form-item label="额外提示">
          <el-input v-model="form.extra_instruction" type="textarea" :rows="4" placeholder="补充该品种的特殊关注点，例如成本端、季节性、进口窗口等。" />
        </el-form-item>
        <el-form-item label="输出偏好">
          <el-input v-model="form.output_preference" type="textarea" :rows="3" placeholder="例如：先方向，再驱动，再风险，最后附原文依据。" />
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button v-if="form.profile_id" type="danger" plain :icon="Delete" :loading="deleting" @click="handleDelete">
            删除画像
          </el-button>
          <div class="dialog-footer-actions">
            <el-button @click="dialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="submitting" @click="submitForm">保存画像</el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="less" scoped>
.profile-manager {
  padding: 16px;
}
.toolbar {
  display: flex;
  align-items: flex-start;
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
.search-input {
  width: 320px;
  max-width: 100%;
}
.dimension-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.placeholder-text {
  color: #909399;
}
.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.dialog-footer-actions {
  display: flex;
  gap: 12px;
}
</style>
