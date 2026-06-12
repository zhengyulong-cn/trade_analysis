<script lang="ts" setup>
import {
  resolveStorageImageUrl,
  uploadImageApi,
  type ImageAttachment,
  type ImageUploadResult,
  type UploadScope,
} from "@/api/modules"
import {
  ElMessage,
  type UploadFile,
  type UploadProps,
  type UploadRawFile,
  type UploadRequestOptions,
} from "element-plus"
import { computed, onBeforeUnmount, ref, watch } from "vue"

const props = withDefaults(
  defineProps<{
    modelValue: ImageAttachment[]
    scope: UploadScope
    maxCount?: number
    storageLabel?: string
    pasteEnabled?: boolean
    disabled?: boolean
  }>(),
  {
    maxCount: 12,
    storageLabel: "",
    pasteEnabled: true,
    disabled: false,
  },
)

const emit = defineEmits<{
  "update:modelValue": [value: ImageAttachment[]]
}>()

const uploadFiles = ref<UploadFile[]>([])
let uploadUidSeed = 1

const images = computed(() => (Array.isArray(props.modelValue) ? props.modelValue : []))
const tipText = computed(() => {
  const storageText = props.storageLabel ? `图片保存到 ${props.storageLabel}，` : ""
  const pasteText = props.pasteEnabled ? "，支持 Ctrl+V 粘贴截图" : ""
  return `${storageText}最多 ${props.maxCount} 张${pasteText}`
})

const nextUploadUid = () => `image-attachment-${uploadUidSeed++}`

const normalizeImageItem = (item: ImageAttachment): ImageAttachment => ({
  path: item.path,
  original_name: item.original_name,
  content_type: item.content_type,
  size: item.size,
})

const toUploadFile = (image: ImageAttachment): UploadFile => {
  const resolvedUrl = resolveStorageImageUrl(image.path)
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

const toUploadError = (message: string): Error & { status?: number; method?: string; url?: string } => {
  const error = new Error(message) as Error & { status?: number; method?: string; url?: string }
  error.name = "UploadError"
  error.status = 500
  error.method = "POST"
  error.url = ""
  return error
}

const beforeImageUpload = (rawFile: UploadRawFile) => {
  const isImage = ["image/jpeg", "image/png", "image/webp", "image/gif"].includes(rawFile.type)
  if (!isImage) {
    ElMessage.error("只支持 JPG、PNG、WEBP、GIF 图片")
    return false
  }
  return true
}

const emitImages = (nextImages: ImageAttachment[]) => {
  emit("update:modelValue", nextImages.map(normalizeImageItem))
}

const appendUploadedImage = (image: ImageAttachment) => {
  const normalizedImage = normalizeImageItem(image)
  emitImages([...images.value, normalizedImage])
  uploadFiles.value = [...uploadFiles.value, toUploadFile(normalizedImage)]
}

const uploadImage = async (file: File) => {
  if (images.value.length >= props.maxCount) {
    ElMessage.warning(`当前图片字段最多上传 ${props.maxCount} 张`)
    return
  }

  const result = await uploadImageApi(file, props.scope)
  appendUploadedImage(result)
}

const handleUploadRequest = async (options: UploadRequestOptions) => {
  try {
    const result = await uploadImageApi(options.file, props.scope)
    appendUploadedImage(result)
    options.onSuccess?.(result)
  } catch {
    options.onError?.(toUploadError("截图上传失败"))
  }
}

const resolveUploadPath = (uploadFile: UploadFile) => {
  const response = uploadFile.response as ImageUploadResult | ImageAttachment | undefined
  if (response?.path) {
    return response.path
  }
  if (!uploadFile.url) {
    return ""
  }
  return uploadFile.url.replace(/^.*\/storage\//, "")
}

const handleUploadRemove: UploadProps["onRemove"] = (uploadFile, nextUploadFiles) => {
  const removedPath = resolveUploadPath(uploadFile)
  emitImages(images.value.filter((item) => item.path !== removedPath))
  uploadFiles.value = [...nextUploadFiles]
}

const handlePaste = async (event: ClipboardEvent) => {
  if (!props.pasteEnabled || props.disabled) {
    return
  }

  const clipboardItems = event.clipboardData?.items
  if (!clipboardItems?.length) {
    return
  }

  const imageItem = Array.from(clipboardItems).find((item) => item.type.startsWith("image/"))
  if (!imageItem) {
    return
  }

  const file = imageItem.getAsFile()
  if (!file) {
    return
  }

  event.preventDefault()

  try {
    await uploadImage(file)
    ElMessage.success("图片已粘贴上传")
  } catch {
    ElMessage.error("截图上传失败")
  }
}

watch(
  images,
  (value) => {
    uploadFiles.value = value.map(toUploadFile)
  },
  { immediate: true, deep: true },
)

watch(
  () => props.pasteEnabled,
  (enabled) => {
    if (enabled) {
      window.addEventListener("paste", handlePaste)
    } else {
      window.removeEventListener("paste", handlePaste)
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  window.removeEventListener("paste", handlePaste)
})
</script>

<template>
  <div class="image-attachment-upload">
    <el-upload
      :file-list="uploadFiles"
      list-type="picture-card"
      :auto-upload="true"
      :limit="maxCount"
      :disabled="disabled"
      :before-upload="beforeImageUpload"
      :http-request="handleUploadRequest"
      :on-remove="handleUploadRemove"
      accept="image/jpeg,image/png,image/webp,image/gif"
    >
      <el-icon><Plus /></el-icon>
    </el-upload>
    <div class="upload-tip">{{ tipText }}</div>
  </div>
</template>

<style scoped lang="less">
.image-attachment-upload {
  display: inline-block;
}

.upload-tip {
  margin-top: 8px;
  color: #8c98aa;
  font-size: 12px;
}
</style>
