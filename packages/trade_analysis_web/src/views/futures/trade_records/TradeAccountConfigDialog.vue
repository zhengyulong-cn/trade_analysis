<script lang="ts" setup>
import {
  createTradeAccountApi,
  deleteTradeAccountApi,
  updateTradeAccountApi,
  type TradeAccount,
  type TradeAccountType,
} from "@/api/modules"
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from "element-plus"
import { computed, reactive, ref, watch } from "vue"

interface AccountForm {
  account_id?: number
  account_name: string
  account_type: TradeAccountType
  account_no: string
  password: string
}

const props = defineProps<{
  modelValue: boolean
  accounts: TradeAccount[]
}>()

const emit = defineEmits<{
  "update:modelValue": [value: boolean]
  changed: []
}>()

const ACCOUNT_TYPE_OPTIONS: Array<{ label: string; value: TradeAccountType }> = [
  { label: "实盘", value: "real" },
  { label: "模拟", value: "simulated" },
]

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit("update:modelValue", value),
})

const accountSubmitting = ref(false)
const accountFormRef = ref<FormInstance>()
const selectedAccountId = ref<number | null>(null)
const localAccounts = ref<TradeAccount[]>([])
const accountForm = reactive<AccountForm>({
  account_name: "",
  account_type: "real",
  account_no: "",
  password: "",
})

const sortedAccounts = computed(() => [...localAccounts.value].sort((a, b) => a.account_id - b.account_id))
const editorTitle = computed(() => (selectedAccountId.value === null ? "新增账户" : "编辑账户"))

const accountRules = reactive<FormRules<AccountForm>>({
  account_name: [{ required: true, message: "请输入账户名称", trigger: "blur" }],
  account_type: [{ required: true, message: "请选择账户类型", trigger: "change" }],
  account_no: [{ required: true, message: "请输入账户", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
})

watch(
  () => props.accounts,
  (value) => {
    localAccounts.value = [...value]
  },
  { immediate: true },
)

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      resetAccountForm()
    }
  },
)

const resetAccountForm = () => {
  selectedAccountId.value = null
  accountForm.account_id = undefined
  accountForm.account_name = ""
  accountForm.account_type = "real"
  accountForm.account_no = ""
  accountForm.password = ""
  accountFormRef.value?.clearValidate()
}

const editAccount = (account?: TradeAccount | null) => {
  if (!account) {
    return
  }

  selectedAccountId.value = account.account_id
  accountForm.account_id = account.account_id
  accountForm.account_name = account.account_name
  accountForm.account_type = account.account_type
  accountForm.account_no = account.account_no
  accountForm.password = account.password
  accountFormRef.value?.clearValidate()
}

const createDefaultAccount = async () => {
  accountSubmitting.value = true
  try {
    const created = await createTradeAccountApi({
      account_name: "new_account",
      account_type: "real",
      account_no: "new_account_no",
      password: "password",
    })
    localAccounts.value = [...localAccounts.value, created]
    ElMessage.success("已创建新的账户配置")
    editAccount(created)
    emit("changed")
  } catch {
    ElMessage.error("创建新的账户配置失败")
  } finally {
    accountSubmitting.value = false
  }
}

const submitAccountForm = async () => {
  if (!accountFormRef.value) {
    return
  }

  const valid = await accountFormRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }

  accountSubmitting.value = true
  try {
    if (selectedAccountId.value === null) {
      const created = await createTradeAccountApi({
        account_name: accountForm.account_name.trim(),
        account_type: accountForm.account_type,
        account_no: accountForm.account_no.trim(),
        password: accountForm.password,
      })
      localAccounts.value = [...localAccounts.value, created]
      selectedAccountId.value = created.account_id
      accountForm.account_id = created.account_id
      ElMessage.success("账户已创建")
    } else {
      const updated = await updateTradeAccountApi({
        account_id: selectedAccountId.value,
        account_name: accountForm.account_name.trim(),
        account_type: accountForm.account_type,
        account_no: accountForm.account_no.trim(),
        password: accountForm.password,
      })
      localAccounts.value = localAccounts.value.map((item) =>
        item.account_id === updated.account_id ? updated : item,
      )
      editAccount(updated)
      ElMessage.success("账户已更新")
    }

    emit("changed")
  } catch {
    ElMessage.error("保存账户配置失败")
  } finally {
    accountSubmitting.value = false
  }
}

const handleDeleteAccount = async (account: TradeAccount) => {
  try {
    await ElMessageBox.confirm(`确认删除账户【${account.account_name}】吗？`, "删除账户配置", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    })
  } catch {
    return
  }

  try {
    await deleteTradeAccountApi(account.account_id)
    localAccounts.value = localAccounts.value.filter((item) => item.account_id !== account.account_id)
    if (selectedAccountId.value === account.account_id) {
      resetAccountForm()
    }
    ElMessage.success("账户已删除")
    emit("changed")
  } catch {
    ElMessage.error("删除账户配置失败")
  }
}

const handleClosed = () => {
  resetAccountForm()
}
</script>

<template>
  <el-dialog v-model="dialogVisible" title="账户配置" width="1200px" destroy-on-close @closed="handleClosed">
    <div class="account-config-layout">
      <div class="account-config-list">
        <div class="list-header">
          <div class="section-title">已有账户</div>
          <el-button size="small" :loading="accountSubmitting" @click="createDefaultAccount">新增账户配置</el-button>
        </div>
        <el-table :data="sortedAccounts" border height="520" highlight-current-row @current-change="editAccount">
          <el-table-column prop="account_name" label="账户名称" min-width="140" />
          <el-table-column prop="account_type" label="类型" width="100" />
          <el-table-column prop="account_no" label="账户" min-width="160" />
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button link type="danger" @click.stop="handleDeleteAccount(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="account-config-editor">
        <div class="editor-header">
          <div class="section-title">{{ editorTitle }}</div>
          <el-button text @click="resetAccountForm">重置</el-button>
        </div>

        <el-form ref="accountFormRef" :model="accountForm" :rules="accountRules" label-position="top" class="account-form">
          <div class="account-form-grid">
            <el-form-item label="账户名称" prop="account_name">
              <el-input v-model="accountForm.account_name" placeholder="例如：主账户" />
            </el-form-item>

            <el-form-item label="账户类型" prop="account_type">
              <el-select v-model="accountForm.account_type" class="full-width">
                <el-option
                  v-for="option in ACCOUNT_TYPE_OPTIONS"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="账户" prop="account_no">
              <el-input v-model="accountForm.account_no" placeholder="请输入账户" />
            </el-form-item>

            <el-form-item label="密码" prop="password">
              <el-input v-model="accountForm.password" type="password" show-password placeholder="请输入密码" />
            </el-form-item>
          </div>
        </el-form>

        <div class="dialog-footer">
          <el-button @click="resetAccountForm">清空</el-button>
          <el-button type="primary" :loading="accountSubmitting" @click="submitAccountForm">保存账户配置</el-button>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped lang="less">
.account-config-layout {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 20px;
  align-items: start;
}

.account-config-list,
.account-config-editor {
  min-width: 0;
}

.account-config-list {
  padding-right: 4px;
}

.account-config-editor {
  padding-left: 4px;
  border-left: 1px solid #ebeef5;
}

.list-header,
.editor-header,
.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.list-header {
  margin-bottom: 12px;
}

.dialog-footer {
  justify-content: flex-end;
}

.section-title {
  color: #1a2233;
  font-size: 16px;
  font-weight: 700;
}

.account-form {
  padding-top: 4px;
}

.account-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.full-width {
  width: 100%;
}

@media (max-width: 1280px) {
  .account-config-layout {
    grid-template-columns: 1fr;
  }

  .account-config-editor {
    padding-left: 0;
    border-left: none;
    border-top: 1px solid #ebeef5;
    padding-top: 20px;
  }
}

@media (max-width: 900px) {
  .account-form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
