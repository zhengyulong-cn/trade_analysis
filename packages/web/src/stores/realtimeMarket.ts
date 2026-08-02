import { ref } from 'vue'
import { defineStore } from 'pinia'

export interface RealtimeQuote {
  symbol: string
  exchange: string
  last_price: string
  volume: string
  hold: string
  quote_time: string
}

export interface RealtimeBar {
  symbol: string
  exchange: string
  interval: number
  bucket_start: string
  bucket_end: string
  date_time: string
  open: string | number
  high: string | number
  low: string | number
  close: string | number
  volume: string | number
  hold: string | number
}

type RealtimeMessage = {
  type: 'quote' | 'bar'
  data: RealtimeQuote | RealtimeBar
} | {
  type: 'snapshot'
  quotes: RealtimeQuote[]
  bars: RealtimeBar[]
}

const getWebSocketUrl = () => {
  const apiBaseUrl = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '')
  if (/^https?:\/\//i.test(apiBaseUrl)) {
    const url = new URL(apiBaseUrl)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    url.pathname = `${url.pathname}/ws/market`.replace(/\/+/g, '/')
    return url.toString()
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${apiBaseUrl}/ws/market`
}

const getBarKey = (symbol: string, interval: number) => `${symbol}:${interval}`

export const useRealtimeMarketStore = defineStore('realtime-market', () => {
  const quotes = ref<Record<string, RealtimeQuote>>({})
  const bars = ref<Record<string, RealtimeBar>>({})
  const connected = ref(false)
  const subscribedSymbols = ref<string[]>([])
  let socket: WebSocket | null = null
  let reconnectTimer: number | null = null
  let shouldReconnect = false

  const clearReconnectTimer = () => {
    if (reconnectTimer !== null) {
      window.clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  const sendSubscription = () => {
    if (socket?.readyState !== WebSocket.OPEN) {
      return
    }
    socket.send(JSON.stringify({ action: 'subscribe', symbols: subscribedSymbols.value }))
  }

  const applyQuote = (quote: RealtimeQuote) => {
    quotes.value = { ...quotes.value, [quote.symbol]: quote }
  }

  const applyBar = (bar: RealtimeBar) => {
    bars.value = { ...bars.value, [getBarKey(bar.symbol, bar.interval)]: bar }
  }

  const handleMessage = (event: MessageEvent<string>) => {
    let message: RealtimeMessage
    try {
      message = JSON.parse(event.data) as RealtimeMessage
    } catch {
      return
    }

    if (message.type === 'quote') {
      applyQuote(message.data as RealtimeQuote)
      return
    }
    if (message.type === 'bar') {
      applyBar(message.data as RealtimeBar)
      return
    }
    if (message.type === 'snapshot') {
      message.quotes.forEach(applyQuote)
      message.bars.forEach(applyBar)
    }
  }

  const scheduleReconnect = () => {
    if (!shouldReconnect || reconnectTimer !== null) {
      return
    }
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null
      connect()
    }, 3000)
  }

  const connect = () => {
    if (socket?.readyState === WebSocket.OPEN || socket?.readyState === WebSocket.CONNECTING) {
      return
    }
    clearReconnectTimer()
    socket = new WebSocket(getWebSocketUrl())
    socket.onopen = () => {
      connected.value = true
      sendSubscription()
    }
    socket.onmessage = handleMessage
    socket.onclose = () => {
      connected.value = false
      socket = null
      scheduleReconnect()
    }
    socket.onerror = () => socket?.close()
  }

  const subscribe = (symbols: string[]) => {
    subscribedSymbols.value = [...new Set(symbols.map((symbol) => symbol.trim()).filter(Boolean))]
    shouldReconnect = true
    connect()
    sendSubscription()
  }

  const disconnect = () => {
    shouldReconnect = false
    clearReconnectTimer()
    socket?.close()
    socket = null
    connected.value = false
  }

  return {
    quotes,
    bars,
    connected,
    subscribe,
    disconnect,
  }
})
