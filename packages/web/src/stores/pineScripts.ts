import { defineStore } from "pinia"
import { computed, ref } from "vue"

import { getPineScriptListApi, type PineScript } from "@/api/modules"

export const usePineScriptsStore = defineStore("pine-scripts", () => {
  const scripts = ref<PineScript[]>([])
  const loading = ref(false)
  const loaded = ref(false)
  const loadError = ref<string | null>(null)
  let pendingLoad: Promise<PineScript[]> | null = null

  const scriptsById = computed(() => new Map(scripts.value.map((script) => [script.script_id, script])))

  const loadScripts = (force = false) => {
    if (pendingLoad) {
      return pendingLoad
    }
    if (loaded.value && !force) {
      return Promise.resolve(scripts.value)
    }

    loading.value = true
    loadError.value = null
    pendingLoad = getPineScriptListApi()
      .then((items) => {
        scripts.value = items
        loaded.value = true
        return scripts.value
      })
      .catch((error: unknown) => {
        loadError.value = error instanceof Error ? error.message : "Failed to load Pine scripts"
        throw error
      })
      .finally(() => {
        loading.value = false
        pendingLoad = null
      })
    return pendingLoad
  }

  const upsertScript = (script: PineScript) => {
    const index = scripts.value.findIndex((item) => item.script_id === script.script_id)
    scripts.value = index === -1
      ? [...scripts.value, script]
      : scripts.value.map((item) => item.script_id === script.script_id ? script : item)
    loaded.value = true
  }

  const removeScript = (scriptId: number) => {
    scripts.value = scripts.value.filter((script) => script.script_id !== scriptId)
  }

  return {
    scripts,
    loading,
    loaded,
    loadError,
    scriptsById,
    loadScripts,
    upsertScript,
    removeScript,
  }
})
