// WebSocket connection manager for the control system
// This handles real-time updates from the LCU and DCU hardware

export type WebSocketStatus = "connected" | "connecting" | "disconnected" | "error"

type StatusChangeCallback = (status: WebSocketStatus) => void
type MessageCallback = (data: Record<string, number | string>) => void

interface WebSocketManagerOptions {
  url: string
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

class WebSocketManager {
  private socket: WebSocket | null = null
  private status: WebSocketStatus = "disconnected"
  private reconnectInterval: number
  private maxReconnectAttempts: number
  private reconnectAttempts = 0
  private url: string
  private messageHandlers: Map<string, MessageCallback[]> = new Map()
  private statusChangeCallbacks: StatusChangeCallback[] = []

  constructor(options: WebSocketManagerOptions) {
    this.url = options.url
    this.reconnectInterval = options.reconnectInterval || 3000
    this.maxReconnectAttempts = options.maxReconnectAttempts || 5
  }

  // Connect to the WebSocket server
  connect(): void {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      console.log("WebSocket already connected or connecting")
      return
    }

    this.setStatus("connecting")

    try {
      this.socket = new WebSocket(this.url)

      this.socket.onopen = this.handleOpen.bind(this)
      this.socket.onmessage = this.handleMessage.bind(this)
      this.socket.onclose = this.handleClose.bind(this)
      this.socket.onerror = this.handleError.bind(this)
    } catch (error) {
      console.error("Failed to create WebSocket connection:", error)
      this.setStatus("error")
      this.attemptReconnect()
    }
  }

  // Disconnect from the WebSocket server
  disconnect(): void {
    if (this.socket) {
      this.socket.close()
      this.socket = null
      this.setStatus("disconnected")
    }
  }

  // Register a handler for a specific message type
  on(messageType: string, handler: MessageCallback): void {
    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, [])
    }
    this.messageHandlers.get(messageType)?.push(handler)
  }

  // Remove a handler for a specific message type
  off(messageType: string, handler: MessageCallback): void {
    if (!this.messageHandlers.has(messageType)) return

    const handlers = this.messageHandlers.get(messageType)
    if (handlers) {
      const index = handlers.indexOf(handler)
      if (index !== -1) {
        handlers.splice(index, 1)
      }
    }
  }

  // Register a callback for connection status changes
  onStatusChange(callback: StatusChangeCallback): void {
    this.statusChangeCallbacks.push(callback)
    // Immediately call with current status
    callback(this.status)
  }

  // Get the current connection status
  getStatus(): WebSocketStatus {
    return this.status
  }

  // Send a message to the WebSocket server
  send(message: string | object): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      const messageStr = typeof message === 'string' ? message : JSON.stringify(message)
      this.socket.send(messageStr)
    } else {
      console.warn("WebSocket is not connected, cannot send message")
    }
  }

  // Private methods
  private setStatus(status: WebSocketStatus): void {
    this.status = status
    this.statusChangeCallbacks.forEach((callback) => callback(status))
  }

  private handleOpen() {
    this.status = "connected"
    this.notifyStatusChange()
  }

  private handleClose() {
    this.status = "disconnected"
    this.notifyStatusChange()
  }

  private handleError() {
    this.status = "error"
    this.notifyStatusChange()
  }

  private handleMessage(event: MessageEvent) {
    try {
      const message = JSON.parse(event.data)
      
      // Handle different message formats
      if (message.type && message.data) {
        // New format with type and data
        this.notifyMessageHandlers(message.type, message.data)
      } else {
        // Legacy format - treat as generic data
        this.notifyMessageHandlers("data", message)
      }
    } catch (error) {
      console.error("Failed to parse WebSocket message:", error)
    }
  }

  private notifyStatusChange() {
    this.statusChangeCallbacks.forEach((callback) => callback(this.status))
  }

  private notifyMessageHandlers(type: string, data: Record<string, number | string>) {
    const handlers = this.messageHandlers.get(type)
    if (handlers) {
      handlers.forEach(handler => handler(data))
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log("Max reconnect attempts reached")
      return
    }

    this.reconnectAttempts++
    console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`)

    setTimeout(() => {
      this.connect()
    }, this.reconnectInterval)
  }
}

// Create and export a singleton instance
export const websocket = new WebSocketManager({
  url: process.env.NEXT_PUBLIC_WEBSOCKET_URL || "ws://localhost:8000/ws",
  // url: process.env.NEXT_PUBLIC_WEBSOCKET_URL || "ws://10.147.18.184:8000/ws",
  reconnectInterval: 3000,
})
