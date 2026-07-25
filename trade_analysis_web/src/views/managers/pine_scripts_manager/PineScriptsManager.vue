<script lang="ts" setup>
import {
  createPineScriptApi,
  deletePineScriptApi,
  getPineScriptListApi,
  updatePineScriptApi,
  type PineScript,
  type PineScriptCreateParams,
  type PineScriptType,
} from "@/api/modules"
import { formatDateTime } from "@/utils/date"
import { Delete, Edit, Plus, Refresh, Search } from "@element-plus/icons-vue"
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from "element-plus"
import { computed, onMounted, reactive, ref } from "vue"

interface PineScriptForm {
  script_id?: number
  script_name: string
  script_type: PineScriptType
  script_content: string
}

type DialogMode = "create" | "edit"
type TypeFilter = PineScriptType | "all"

const scriptTypeOptions: Array<{ label: string; value: PineScriptType }> = [
  { label: "指标", value: "indicator" },
  { label: "策略", value: "strategy" },
  { label: "扫描器", value: "scanner" },
]

const scripts = ref<PineScript[]>([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const dialogMode = ref<DialogMode>("create")
const typeFilter = ref<TypeFilter>("all")
const keyword = ref("")
const formRef = ref<FormInstance>()

const form = reactive<PineScriptForm>({
  script_name: "",
  script_type: "indicator",
  script_content: "",
})

const rules = reactive<FormRules<PineScriptForm>>({
  script_name: [{ required: true, message: "请输入脚本名称", trigger: "blur" }],
  script_type: [{ required: true, message: "请选择脚本类型", trigger: "change" }],
  script_content: [
    {
      validator: (_rule, value: string, callback) => {
        if (!value || !value.trim()) {
          callback(new Error("请输入脚本内容"))
          return
        }
        callback()
      },
      trigger: "blur",
    },
  ],
})

const dialogTitle = computed(() => (dialogMode.value === "create" ? "新增 Pine 脚本" : "编辑 Pine 脚本"))

const filteredScripts = computed(() => {
  const normalizedKeyword = keyword.value.trim().toLowerCase()
  return scripts.value.filter((item) => {
    const matchesType = typeFilter.value === "all" || item.script_type === typeFilter.value
    if (!matchesType) {
      return false
    }
    if (!normalizedKeyword) {
      return true
    }
    return (
      String(item.script_id).includes(normalizedKeyword) ||
      item.script_name.toLowerCase().includes(normalizedKeyword) ||
      item.script_content.toLowerCase().includes(normalizedKeyword)
    )
  })
})

const getTypeLabel = (type: PineScriptType) => {
  return scriptTypeOptions.find((item) => item.value === type)?.label ?? type
}

const getScriptLineCount = (content: string) => {
  if (!content) {
    return 0
  }
  return content.split(/\r\n|\r|\n/).length
}

const getScriptPreview = (content: string) => {
  const lines = content.split(/\r\n|\r|\n/).filter((line) => line.trim())
  return lines.slice(0, 4).join("\n") || "空脚本"
}

const resetForm = () => {
  form.script_id = undefined
  form.script_name = ""
  form.script_type = "indicator"
  form.script_content = ""
  formRef.value?.clearValidate()
}

const buildPayload = (): PineScriptCreateParams => ({
  script_name: form.script_name.trim(),
  script_type: form.script_type,
  script_content: form.script_content,
})

const loadScripts = async () => {
  loading.value = true
  try {
    scripts.value = await getPineScriptListApi()
  } catch {
    ElMessage.error("获取 Pine 脚本列表失败")
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  dialogMode.value = "create"
  resetForm()
  dialogVisible.value = true
}

const openEditDialog = (script: PineScript) => {
  dialogMode.value = "edit"
  form.script_id = script.script_id
  form.script_name = script.script_name
  form.script_type = script.script_type
  form.script_content = script.script_content
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
    if (dialogMode.value === "create") {
      await createPineScriptApi(buildPayload())
      ElMessage.success("Pine 脚本已新增")
    } else if (form.script_id) {
      await updatePineScriptApi({
        script_id: form.script_id,
        ...buildPayload(),
      })
      ElMessage.success("Pine 脚本已更新")
    }

    dialogVisible.value = false
    await loadScripts()
  } catch {
    ElMessage.error(dialogMode.value === "create" ? "新增 Pine 脚本失败" : "更新 Pine 脚本失败")
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (script: PineScript) => {
  try {
    await ElMessageBox.confirm(`确认删除脚本「${script.script_name}」吗？删除后无法恢复。`, "删除 Pine 脚本", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    })
  } catch {
    return
  }

  try {
    await deletePineScriptApi(script.script_id)
    ElMessage.success("Pine 脚本已删除")
    await loadScripts()
  } catch {
    ElMessage.error("删除 Pine 脚本失败")
  }
}

onMounted(loadScripts)
</script>

<template>
  <section class="pageBox pine-script-manager">
    <header class="toolbar">
      <div class="toolbar-left">
        <h2 class="title">Pine 脚本管理</h2>
        <p class="subtitle">维护指标和策略脚本，适合保存较长的 Pine Script 内容</p>
      </div>

      <div class="toolbar-actions">
        <el-input
          v-model="keyword"
          clearable
          placeholder="搜索 ID、名称或脚本内容"
          class="keyword-input"
          :prefix-icon="Search"
        />
        <el-select v-model="typeFilter" class="type-filter">
          <el-option label="全部类型" value="all" />
          <el-option v-for="option in scriptTypeOptions" :key="option.value" :label="option.label" :value="option.value" />
        </el-select>
        <el-button :icon="Refresh" @click="loadScripts">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreateDialog">新增脚本</el-button>
      </div>
    </header>

    <el-table
      v-loading="loading"
      :data="filteredScripts"
      border
      stripe
      row-key="script_id"
      empty-text="暂无 Pine 脚本"
      class="script-table"
    >
      <el-table-column prop="script_id" label="脚本 ID" width="100" fixed="left" />
      <el-table-column prop="script_name" label="脚本名称" min-width="180" fixed="left" show-overflow-tooltip />
      <el-table-column prop="script_type" label="脚本类型" width="110">
        <template #default="{ row }">
          <el-tag :type="row.script_type === 'strategy' ? 'warning' : 'success'" effect="light">
            {{ getTypeLabel(row.script_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="脚本内容预览" min-width="360">
        <template #default="{ row }">
          <pre class="script-preview">{{ getScriptPreview(row.script_content) }}</pre>
        </template>
      </el-table-column>
      <el-table-column label="行数" width="90">
        <template #default="{ row }">{{ getScriptLineCount(row.script_content) }}</template>
      </el-table-column>
      <el-table-column label="字符数" width="100">
        <template #default="{ row }">{{ row.script_content.length }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" min-width="180">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column prop="updated_at" label="更新时间" min-width="180">
        <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" :icon="Edit" @click="openEditDialog(row)">编辑</el-button>
          <el-button link type="danger" :icon="Delete" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="86vw"
      destroy-on-close
      class="script-dialog"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="script-form">
        <el-form-item label="脚本名称" prop="script_name">
          <el-input
            v-model.trim="form.script_name"
            maxlength="200"
            placeholder="请输入脚本名称"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="脚本类型" prop="script_type">
          <el-radio-group v-model="form.script_type">
            <el-radio-button v-for="option in scriptTypeOptions" :key="option.value" :label="option.value">
              {{ option.label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="脚本内容" prop="script_content">
          <el-input
            v-model="form.script_content"
            type="textarea"
            resize="vertical"
            placeholder="粘贴或输入 Pine Script 内容"
            class="script-textarea"
            :autosize="{ minRows: 24, maxRows: 34 }"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <div class="script-counter">
            {{ getScriptLineCount(form.script_content) }} 行 / {{ form.script_content.length }} 字符
          </div>
          <div class="dialog-actions">
            <el-button @click="dialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped lang="less">
.pine-script-manager {
  padding: 16px;
}

.toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.toolbar-left {
  min-width: 0;
}

.title {
  margin: 0;
  color: #1f2a37;
  font-size: 20px;
  font-weight: 700;
}

.subtitle {
  margin: 6px 0 0;
  color: #7c8798;
  font-size: 13px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 10px;
}

.keyword-input {
  width: 240px;
}

.type-filter {
  width: 130px;
}

.script-table {
  width: 100%;
}

.script-preview {
  max-height: 112px;
  margin: 0;
  overflow: hidden;
  color: #344054;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.script-form {
  padding-top: 2px;
}

.script-textarea {
  width: 100%;
}

.script-textarea :deep(.el-textarea__inner) {
  min-height: 520px !important;
  font-family: Consolas, "Courier New", monospace;
  font-size: 13px;
  line-height: 1.55;
  tab-size: 2;
}

.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.script-counter {
  color: #7c8798;
  font-size: 13px;
}

.dialog-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

@media (max-width: 900px) {
  .toolbar {
    flex-direction: column;
  }

  .toolbar-actions,
  .keyword-input,
  .type-filter {
    width: 100%;
  }

  .script-textarea :deep(.el-textarea__inner) {
    min-height: 420px !important;
  }

  .dialog-footer {
    flex-direction: column;
    align-items: stretch;
  }

  .dialog-actions {
    justify-content: flex-end;
  }
}
</style>
