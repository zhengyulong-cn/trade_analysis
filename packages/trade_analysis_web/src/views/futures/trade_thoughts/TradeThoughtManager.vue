<script lang="ts" setup>
import {
  createTradeThoughtApi,
  deleteTradeThoughtApi,
  getFutureContractList,
  getTradeThoughtListApi,
  resolveTradeThoughtImageUrl,
  updateTradeThoughtApi,
  uploadTradeThoughtImageApi,
  type FutureContract,
  type TradeThought,
  type TradeThoughtCreateParams,
  type TradeThoughtImage,
  type TradeThoughtImageUploadResult,
  type TradeThoughtUpdateParams,
} from "@/api/modules"
import { formatDateTime } from "@/utils/date"
import {
  ElMessage,
  ElMessageBox,
  type FormInstance,
  type FormRules,
  type UploadFile,
  type UploadProps,
  type UploadRawFile,
  type UploadRequestOptions,
} from "element-plus"
import { computed, onMounted, reactive, ref } from "vue"

interface TradeThoughtForm {
  thought_id?: number
  title: string
  categories: string
  content: string
  codes: string[]
  images: TradeThoughtImage[]
}

const MAX_IMAGE_COUNT = 9

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const dialogMode = ref<"create" | "edit">("create")
const contracts = ref<FutureContract[]>([])
const thoughts = ref<TradeThought[]>([])
const formRef = ref<FormInstance>()
const uploadFileList = ref<UploadFile[]>([])
let uploadUidSeed = 1

const form = reactive<TradeThoughtForm>({
  title: "",
  categories: "",
  content: "",
  codes: [],
  images: [],
})

const rules = reactive<FormRules<TradeThoughtForm>>({
  content: [{ required: true, message: "请输入小记内容", trigger: "blur" }],
})

const contractCodeOptions = computed(() => {
  const seen = new Set<string>()
  const options: string[] = []

  for (const item of contracts.value) {
    const symbol = item.symbol.trim()
    if (symbol && !seen.has(symbol)) {
      seen.add(symbol)
      options.push(symbol)
    }
  }

  return options
})

const dialogTitle = computed(() => (dialogMode.value === "create" ? "发布交易小记" : "编辑交易小记"))
const recentCount = computed(() => thoughts.value.slice(0, 7).length)

const nextUploadUid = () => uploadUidSeed++

const toUploadError = (message: string): Error & { status?: number; method?: string; url?: string } => {
  const error = new Error(message) as Error & { status?: number; method?: string; url?: string }
  error.name = "UploadError"
  error.status = 500
  error.method = "POST"
  error.url = ""
  return error
}

const toUploadFile = (image: TradeThoughtImage): UploadFile => {
  const resolvedUrl = resolveTradeThoughtImageUrl(image.path)
  return {
    uid: nextUploadUid(),
    name: image.original_name,
    url: resolvedUrl,
    status: "success",
    response: {
      ...image,
      url: resolvedUrl,
    },
  }
}

const resetForm = () => {
  form.thought_id = undefined
  form.title = ""
  form.categories = ""
  form.content = ""
  form.codes = []
  form.images = []
  uploadFileList.value = []
  formRef.value?.clearValidate()
}

const normalizeCodes = (codes: string[]) => {
  const result: string[] = []
  const seen = new Set<string>()

  for (const item of codes) {
    const text = item.trim()
    if (!text || seen.has(text)) {
      continue
    }
    result.push(text)
    seen.add(text)
  }

  return result
}

const buildPayload = (): TradeThoughtCreateParams => {
  return {
    title: form.title.trim() || null,
    categories: form.categories.trim() || null,
    content: form.content.trim(),
    codes: normalizeCodes(form.codes),
    images: [...form.images],
  }
}

const loadContracts = async () => {
  try {
    contracts.value = await getFutureContractList()
  } catch {
    ElMessage.error("获取合约列表失败")
  }
}

const loadTradeThoughts = async () => {
  loading.value = true
  try {
    thoughts.value = await getTradeThoughtListApi()
  } catch {
    ElMessage.error("获取交易小记失败")
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  dialogMode.value = "create"
  resetForm()
  dialogVisible.value = true
}

const openEditDialog = (thought: TradeThought) => {
  dialogMode.value = "edit"
  form.thought_id = thought.thought_id
  form.title = thought.title ?? ""
  form.categories = thought.categories ?? ""
  form.content = thought.content
  form.codes = [...thought.codes]
  form.images = [...thought.images]
  uploadFileList.value = thought.images.map(toUploadFile)
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
      await createTradeThoughtApi(buildPayload())
      ElMessage.success("交易小记已发布")
    } else if (form.thought_id) {
      const payload: TradeThoughtUpdateParams = {
        thought_id: form.thought_id,
        ...buildPayload(),
      }
      await updateTradeThoughtApi(payload)
      ElMessage.success("交易小记已更新")
    }

    dialogVisible.value = false
    resetForm()
    await loadTradeThoughts()
  } catch {
    ElMessage.error(dialogMode.value === "create" ? "发布交易小记失败" : "更新交易小记失败")
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (thought: TradeThought) => {
  try {
    await ElMessageBox.confirm("删除后无法恢复，确认继续吗？", "删除交易小记", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    })
  } catch {
    return
  }

  try {
    await deleteTradeThoughtApi(thought.thought_id)
    ElMessage.success("交易小记已删除")
    await loadTradeThoughts()
  } catch {
    ElMessage.error("删除交易小记失败")
  }
}

const beforeImageUpload = (rawFile: UploadRawFile) => {
  const isImage = ["image/jpeg", "image/png", "image/webp", "image/gif"].includes(rawFile.type)
  if (!isImage) {
    ElMessage.error("只支持 JPG、PNG、WEBP、GIF 图片")
    return false
  }

  const isLimitExceeded = uploadFileList.value.length >= MAX_IMAGE_COUNT
  if (isLimitExceeded) {
    ElMessage.error(`最多上传 ${MAX_IMAGE_COUNT} 张图片`)
    return false
  }

  return true
}

const handleUploadRequest = async (options: UploadRequestOptions) => {
  try {
    const result = await uploadTradeThoughtImageApi(options.file)
    form.images = [
      ...form.images,
      {
        path: result.path,
        original_name: result.original_name,
        content_type: result.content_type,
        size: result.size,
      },
    ]
    options.onSuccess?.(result)
  } catch {
    options.onError?.(toUploadError("上传图片失败"))
  }
}

const resolveUploadPath = (uploadFile: UploadFile) => {
  const response = uploadFile.response as TradeThoughtImageUploadResult | TradeThoughtImage | undefined
  if (response?.path) {
    return response.path
  }
  if (!uploadFile.url) {
    return ""
  }
  return uploadFile.url.replace(/^.*\/storage\//, "")
}

const handleUploadRemove: UploadProps["onRemove"] = (uploadFile, uploadFiles) => {
  const removedPath = resolveUploadPath(uploadFile)
  form.images = form.images.filter((item) => item.path !== removedPath)
  uploadFileList.value = uploadFiles
}

const handleDialogClosed = () => {
  resetForm()
}

onMounted(async () => {
  await Promise.all([loadContracts(), loadTradeThoughts()])
})
</script>

<template>
  <section class="trade-thought-page">
    <div class="page-shell">
      <section class="hero-panel">
        <div class="hero-copy">
          <span class="eyebrow">Trade Thoughts</span>
          <h1>交易小记</h1>
          <p>把盘中念头、临场观察和截图集中留在一处，轻一点，但足够清晰。</p>
        </div>

        <div class="hero-side">
          <div class="stat-card">
            <strong>{{ thoughts.length }}</strong>
            <span>总小记</span>
          </div>
          <div class="stat-card warm">
            <strong>{{ recentCount }}</strong>
            <span>最近展示</span>
          </div>
          <el-button type="primary" size="large" round class="publish-button" @click="openCreateDialog">
            发布小记
          </el-button>
        </div>
      </section>

      <section class="content-grid">
        <aside class="guide-card">
          <div class="guide-card__header">
            <span class="guide-dot"></span>
            <h3>记录建议</h3>
          </div>
          <ul class="guide-list">
            <li>标题可选，适合给关键判断一个简短结论。</li>
            <li>代码标签支持从合约列表选择，也支持手动录入。</li>
            <li>图片更适合放关键截面，不用追求完整复盘。</li>
            <li>分类建议保持少量固定词，后面更容易自己筛选。</li>
          </ul>
        </aside>

        <el-card shadow="never" class="thought-list-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">时间流</div>
                <div class="card-subtitle">按发布时间倒序展示</div>
              </div>
              <span class="count-pill">{{ thoughts.length }} 条</span>
            </div>
          </template>

          <el-empty v-if="!loading && !thoughts.length" description="还没有交易小记，先发布一条吧" />

          <div v-else v-loading="loading" class="thought-list">
            <article v-for="thought in thoughts" :key="thought.thought_id" class="thought-item">
              <div class="thought-accent"></div>

              <div class="thought-main">
                <div class="thought-topline">
                  <div class="thought-heading">
                    <h3 v-if="thought.title" class="thought-title">{{ thought.title }}</h3>
                    <span v-else class="thought-title thought-title--muted">未填写标题</span>
                    <div class="thought-time-mobile">
                      <span>{{ formatDateTime(thought.created_at) }}</span>
                    </div>
                  </div>

                  <div class="thought-actions">
                    <el-button link type="primary" @click="openEditDialog(thought)">编辑</el-button>
                    <el-button link type="danger" @click="handleDelete(thought)">删除</el-button>
                  </div>
                </div>

                <div v-if="thought.categories || thought.codes.length" class="thought-meta">
                  <span v-if="thought.categories" class="meta-chip meta-chip--category">{{ thought.categories }}</span>
                  <span
                    v-for="code in thought.codes"
                    :key="`${thought.thought_id}-${code}`"
                    class="meta-chip meta-chip--code"
                  >
                    {{ code }}
                  </span>
                </div>

                <p class="thought-content">{{ thought.content }}</p>

                <div v-if="thought.images.length" class="thought-images">
                  <el-image
                    v-for="image in thought.images"
                    :key="image.path"
                    :src="resolveTradeThoughtImageUrl(image.path)"
                    :preview-src-list="thought.images.map((item) => resolveTradeThoughtImageUrl(item.path))"
                    fit="cover"
                    class="thought-image"
                    preview-teleported
                  />
                </div>

                <div class="thought-time">
                  <span>发布于 {{ formatDateTime(thought.created_at) }}</span>
                  <span v-if="thought.updated_at !== thought.created_at">更新于 {{ formatDateTime(thought.updated_at) }}</span>
                </div>
              </div>
            </article>
          </div>
        </el-card>
      </section>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="760px"
      destroy-on-close
      class="thought-dialog"
      @closed="handleDialogClosed"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="thought-form">
        <div class="form-grid">
          <el-form-item label="标题" prop="title">
            <el-input v-model="form.title" maxlength="200" placeholder="可选，方便快速概括这条小记" show-word-limit />
          </el-form-item>

          <el-form-item label="分类" prop="categories">
            <el-input
              v-model="form.categories"
              maxlength="200"
              placeholder="可选，例如：盘前计划、临盘观察、复盘"
              show-word-limit
            />
          </el-form-item>
        </div>

        <el-form-item label="代码标签" prop="codes">
          <el-select
            v-model="form.codes"
            multiple
            filterable
            allow-create
            default-first-option
            clearable
            placeholder="可输入代码，也可从现有合约列表中选择"
            class="codes-select"
          >
            <el-option v-for="code in contractCodeOptions" :key="code" :label="code" :value="code" />
          </el-select>
        </el-form-item>

        <el-form-item label="内容" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="8"
            maxlength="5000"
            placeholder="写下盘中的想法、计划、观察和判断"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="图片">
          <el-upload
            v-model:file-list="uploadFileList"
            list-type="picture-card"
            :auto-upload="true"
            :limit="MAX_IMAGE_COUNT"
            :before-upload="beforeImageUpload"
            :http-request="handleUploadRequest"
            :on-remove="handleUploadRemove"
            accept="image/jpeg,image/png,image/webp,image/gif"
            class="thought-upload"
          >
            <el-icon><Plus /></el-icon>
          </el-upload>
          <div class="upload-tip">最多 {{ MAX_IMAGE_COUNT }} 张，支持 JPG、PNG、WEBP、GIF。</div>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="submitForm">
            {{ dialogMode === "create" ? "发布" : "保存" }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped lang="less">
.trade-thought-page {
  min-height: calc(100vh - 48px);
  padding: 20px;
  background:
    radial-gradient(circle at top left, rgba(214, 233, 255, 0.9), transparent 28%),
    radial-gradient(circle at top right, rgba(255, 228, 209, 0.7), transparent 24%),
    linear-gradient(180deg, #f7f8fc 0%, #eef2f8 100%);
}

.page-shell {
  max-width: 1240px;
  margin: 0 auto;
}

.hero-panel {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 24px;
  padding: 28px 30px;
  border: 1px solid rgba(136, 152, 170, 0.15);
  border-radius: 28px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.94), rgba(245, 249, 255, 0.92)),
    linear-gradient(135deg, #ffffff, #eef5ff);
  box-shadow: 0 22px 50px rgba(39, 70, 110, 0.08);
}

.hero-copy {
  max-width: 640px;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(31, 111, 235, 0.08);
  color: #1f5fd1;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-copy h1 {
  margin: 14px 0 10px;
  font-size: 34px;
  line-height: 1.1;
  color: #152033;
}

.hero-copy p {
  max-width: 560px;
  font-size: 15px;
  line-height: 1.8;
  color: #5f6f86;
}

.hero-side {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: space-between;
  gap: 14px;
  min-width: 220px;
}

.stat-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(20, 35, 59, 0.92);
  color: #fff;
}

.stat-card strong {
  font-size: 24px;
  line-height: 1;
}

.stat-card span {
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
}

.stat-card.warm {
  background: linear-gradient(135deg, #d3693f, #f3ae59);
}

.publish-button {
  height: 46px;
  font-weight: 600;
}

.content-grid {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 20px;
  margin-top: 20px;
}

.guide-card {
  align-self: start;
  padding: 22px 20px;
  border: 1px solid rgba(136, 152, 170, 0.14);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.85);
  box-shadow: 0 16px 40px rgba(56, 79, 118, 0.08);
  backdrop-filter: blur(10px);
}

.guide-card__header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.guide-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1f67d2, #73b4ff);
  box-shadow: 0 0 0 6px rgba(72, 141, 255, 0.12);
}

.guide-card h3 {
  margin: 0;
  font-size: 16px;
  color: #182334;
}

.guide-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  color: #5f6f86;
  font-size: 13px;
  line-height: 1.7;
}

.guide-list li {
  position: relative;
  padding-left: 16px;
}

.guide-list li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 9px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #87a8d9;
}

.thought-list-card {
  border: none;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 18px 44px rgba(56, 79, 118, 0.08);
  backdrop-filter: blur(10px);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.card-title {
  color: #182334;
  font-size: 18px;
  font-weight: 700;
}

.card-subtitle {
  margin-top: 4px;
  color: #7e8ba0;
  font-size: 12px;
}

.count-pill {
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(31, 95, 209, 0.08);
  color: #1f5fd1;
  font-size: 12px;
  font-weight: 600;
}

.thought-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.thought-item {
  position: relative;
  display: flex;
  gap: 14px;
  padding: 22px;
  border: 1px solid rgba(205, 214, 227, 0.72);
  border-radius: 22px;
  background: linear-gradient(180deg, #ffffff, #fbfcff);
  box-shadow: 0 10px 24px rgba(89, 110, 148, 0.06);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    border-color 0.2s ease;
}

.thought-item:hover {
  transform: translateY(-2px);
  border-color: rgba(124, 157, 214, 0.45);
  box-shadow: 0 18px 34px rgba(76, 105, 152, 0.1);
}

.thought-accent {
  width: 4px;
  border-radius: 999px;
  background: linear-gradient(180deg, #1f67d2, #f0a24f);
  flex-shrink: 0;
}

.thought-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.thought-topline {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.thought-heading {
  min-width: 0;
}

.thought-title {
  margin: 0;
  color: #132033;
  font-size: 20px;
  line-height: 1.3;
  font-weight: 700;
}

.thought-title--muted {
  color: #92a0b3;
  font-weight: 500;
}

.thought-time-mobile {
  display: none;
}

.thought-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.thought-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.meta-chip--category {
  background: rgba(240, 162, 79, 0.13);
  color: #b36a1f;
}

.meta-chip--code {
  background: rgba(31, 103, 210, 0.08);
  color: #215bb8;
}

.thought-content {
  margin: 0;
  color: #33445c;
  font-size: 14px;
  line-height: 1.9;
  white-space: pre-wrap;
}

.thought-images {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(128px, 1fr));
  gap: 12px;
}

.thought-image {
  width: 100%;
  height: 128px;
  overflow: hidden;
  border-radius: 16px;
  background: linear-gradient(135deg, #eef3fb, #f7f8fb);
  box-shadow: inset 0 0 0 1px rgba(214, 220, 230, 0.65);
}

.thought-time {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding-top: 14px;
  border-top: 1px dashed rgba(201, 210, 225, 0.8);
  color: #8491a3;
  font-size: 12px;
}

.thought-form {
  padding-top: 4px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.codes-select {
  width: 100%;
}

.thought-upload :deep(.el-upload--picture-card),
.thought-upload :deep(.el-upload-list__item) {
  border-radius: 18px;
}

.upload-tip {
  margin-top: 8px;
  color: #8c98aa;
  font-size: 12px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 1024px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .guide-card {
    order: 2;
  }
}

@media (max-width: 768px) {
  .trade-thought-page {
    padding: 12px;
  }

  .hero-panel {
    flex-direction: column;
    padding: 22px 18px;
    border-radius: 22px;
  }

  .hero-copy h1 {
    font-size: 28px;
  }

  .hero-side {
    min-width: 0;
  }

  .thought-item {
    padding: 16px;
    border-radius: 18px;
  }

  .thought-topline {
    flex-direction: column;
  }

  .thought-actions {
    justify-content: flex-start;
  }

  .thought-time {
    display: none;
  }

  .thought-time-mobile {
    display: block;
    margin-top: 6px;
    color: #8b97aa;
    font-size: 12px;
  }

  .form-grid {
    grid-template-columns: 1fr;
    gap: 0;
  }
}
</style>
