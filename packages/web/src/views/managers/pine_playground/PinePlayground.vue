<script setup lang="ts">
import { Indicator, PineRuntimeError, PineTS } from "pinets"
import { computed, ref } from "vue"
import JsonPretty from "vue-json-pretty"
import "vue-json-pretty/lib/styles.css"

type LocalCandle = {
  openTime: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

const DEFAULT_SOURCE = `
//@version=6
indicator("EMA", overlay = true)
EMA20 = ta.ema(close, 20)
EMA120 = ta.ema(close, 120)
plot(EMA20, title="EMA20", color=color.blue)
plot(EMA120, title="EMA120", color=color.purple)
`

const source = ref(DEFAULT_SOURCE)
const candleCount = ref(1000)
const running = ref(false)
const elapsedMilliseconds = ref<number>()
const result = ref<Record<string, unknown>>()
const errorMessage = ref("")
const debugDetails = ref<Record<string, unknown>>()

const debugDetailsText = computed(() =>
  debugDetails.value ? JSON.stringify(debugDetails.value, null, 2) : "",
)

const createCandles = (count: number): LocalCandle[] => {
  const startTime = Date.UTC(2024, 0, 1)
  const candles: LocalCandle[] = []
  let previousClose = 100

  for (let index = 0; index < count; index += 1) {
    const trend = index * 0.015
    const wave = Math.sin(index / 12) * 2.4 + Math.cos(index / 29) * 1.1
    const open = previousClose
    const close = Math.max(1, 100 + trend + wave)
    const range = 0.6 + Math.abs(Math.sin(index / 5)) * 1.8

    candles.push({
      openTime: startTime + index * 60 * 60 * 1000,
      open,
      high: Math.max(open, close) + range,
      low: Math.min(open, close) - range,
      close,
      volume: 1000 + (index % 80) * 35,
    })
    previousClose = close
  }

  return candles
}

const runScript = async () => {
  running.value = true
  result.value = undefined
  errorMessage.value = ""
  elapsedMilliseconds.value = undefined
  debugDetails.value = undefined
  const startedAt = performance.now()
  const candles = createCandles(candleCount.value)

  try {
    console.groupCollapsed("[PineTS Playground] Execute script")
    console.debug("Source", source.value)
    console.debug("Candles", candles)

    const indicator = new Indicator(source.value)
    const prepared = indicator.prepare({ debug: false, ln: false })
    const transpiledCode = prepared.fn.toString()
    debugDetails.value = {
      sourceLength: source.value.length,
      barCount: candles.length,
      firstCandle: candles[0],
      lastCandle: candles.at(-1),
      inputs: prepared.inputs,
      usesVisibleRange: prepared.usesVisibleRange,
      transpilerDebugEnabled: false,
      transpiledCode,
    }
    console.debug("Prepared inputs", prepared.inputs)
    console.debug("Transpiled code", transpiledCode)

    const pine = new PineTS(candles)
    pine.setDebugSettings({ debug: false, ln: false })
    const context = await pine.run(indicator)
    result.value = {
      indicator: context.indicator,
      plots: context.plots,
      alerts: context.alerts,
      warnings: context.warnings,
    }
    console.info("Execution result", result.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "PineTS execution failed."
    const runtimeError = error instanceof PineRuntimeError ? error : undefined
    debugDetails.value = {
      ...debugDetails.value,
      error: {
        name: error instanceof Error ? error.name : typeof error,
        message: errorMessage.value,
        method: runtimeError?.method,
        stack: error instanceof Error ? error.stack : undefined,
      },
    }
    console.error("[PineTS Playground] Execution failed", error)
  } finally {
    elapsedMilliseconds.value = Math.round(performance.now() - startedAt)
    running.value = false
    console.groupEnd()
  }
}

const restoreSample = () => {
  source.value = DEFAULT_SOURCE
  result.value = undefined
  errorMessage.value = ""
  elapsedMilliseconds.value = undefined
  debugDetails.value = undefined
}
</script>

<template>
  <main class="pine-playground">
    <header class="page-toolbar">
      <div>
        <h1>PineTS Playground</h1>
        <p>Local browser execution</p>
      </div>
      <div class="toolbar-actions">
        <el-input-number v-model="candleCount" :min="10" :max="2000" :step="100" controls-position="right" />
        <el-button @click="restoreSample">Restore Sample</el-button>
        <el-button type="primary" :loading="running" @click="runScript">Run Script</el-button>
      </div>
    </header>

    <section class="workspace">
      <section class="editor-pane">
        <el-input v-model="source" type="textarea" :rows="28" resize="none" spellcheck="false" />
      </section>
      <section class="result-pane">
        <div class="result-meta">
          <span>{{ candleCount }} bars</span>
          <span v-if="elapsedMilliseconds !== undefined">{{ elapsedMilliseconds }} ms</span>
        </div>
        <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" show-icon />
        <JsonPretty
          v-else-if="result"
          :data="result"
          :deep="2"
          show-line
          show-length
          collapsed-on-click-brackets
          class="result-json"
        />
        <el-empty v-else description="Run a script to inspect its output." />
        <el-collapse v-if="debugDetailsText" class="debug-details">
          <el-collapse-item title="Debug details">
            <pre class="debug-output">{{ debugDetailsText }}</pre>
          </el-collapse-item>
        </el-collapse>
      </section>
    </section>
  </main>
</template>

<style scoped lang="less">
.pine-playground {
  min-height: calc(100vh - 4rem);
  padding: 20px;
  background: #f5f7fa;
}

.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

h1,
p {
  margin: 0;
}

h1 {
  color: #1f2937;
  font-size: 20px;
  line-height: 1.4;
}

p {
  margin-top: 4px;
  color: #667085;
  font-size: 13px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  min-height: 650px;
  border: 1px solid #dfe5ef;
  border-radius: 6px;
  overflow: hidden;
  background: #ffffff;
}

.editor-pane,
.result-pane {
  min-width: 0;
  padding: 16px;
}

.editor-pane {
  border-right: 1px solid #dfe5ef;
}

.result-pane {
  display: flex;
  flex-direction: column;
}

.result-meta {
  display: flex;
  gap: 12px;
  min-height: 22px;
  margin-bottom: 12px;
  color: #667085;
  font-size: 13px;
}

.result-json {
  flex: 1;
  min-height: 0;
  padding: 12px;
  overflow: auto;
  border: 1px solid #dfe5ef;
  border-radius: 4px;
  background: #f8fafc;
}

.debug-details {
  margin-top: 12px;
}

.debug-output {
  max-height: 320px;
  margin: 0;
  padding: 12px;
  overflow: auto;
  background: #111827;
  color: #d1d5db;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 900px) {
  .pine-playground {
    padding: 12px;
  }

  .page-toolbar,
  .toolbar-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .workspace {
    grid-template-columns: 1fr;
  }

  .editor-pane {
    border-right: 0;
    border-bottom: 1px solid #dfe5ef;
  }
}
</style>
