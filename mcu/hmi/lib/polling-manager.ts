// Polling-based connection manager for the control system
// This handles periodic API calls to get device status updates

export type PollingStatus = "connected" | "connecting" | "disconnected" | "error"

type StatusChangeCallback = (status: PollingStatus) => void
type MessageCallback = (data: Record<string, unknown>) => void

interface PollingManagerOptions {
  baseUrl: string
  pollInterval?: number
  maxRetries?: number
}

class PollingManager {
  private status: PollingStatus = "disconnected"
  private pollInterval: number
  private maxRetries: number
  private retryCount = 0
  private baseUrl: string
  private messageHandlers: Map<string, MessageCallback[]> = new Map()
  private statusChangeCallbacks: StatusChangeCallback[] = []
  private pollTimer: NodeJS.Timeout | null = null
  private isPolling = false
  private deviceData: Record<string, unknown> = {}

  constructor(options: PollingManagerOptions) {
    this.baseUrl = options.baseUrl
    this.pollInterval = options.pollInterval || 2000 // 2 seconds default
    this.maxRetries = options.maxRetries || 5
  }

  // Start polling for device status
  connect(): void {
    if (this.isPolling) {
      console.log("Polling already active")
      return
    }

    console.log(`Starting polling from: ${this.baseUrl}`)
    this.setStatus("connecting")
    this.startPolling()
  }

  // Stop polling
  disconnect(): void {
    if (this.pollTimer) {
      clearTimeout(this.pollTimer)
      this.pollTimer = null
    }
    this.isPolling = false
    this.setStatus("disconnected")
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
  getStatus(): PollingStatus {
    return this.status
  }

  // Send a message (for compatibility with WebSocket interface)
  send(message: string | object): void {
    console.log("Polling manager received message:", message)
    // For polling, we could implement command sending via API
    // For now, just log the message
  }

  // Private methods
  private setStatus(status: PollingStatus): void {
    if (this.status !== status) {
      console.log(`Polling status changed: ${this.status} → ${status}`)
      this.status = status
      this.statusChangeCallbacks.forEach((callback) => callback(status))
    }
  }

  private async startPolling(): Promise<void> {
    this.isPolling = true
    this.retryCount = 0
    this.setStatus("connected")
    
    const poll = async () => {
      if (!this.isPolling) return

      try {
        await this.fetchDeviceStatus()
        await this.fetchDeviceData()
        this.retryCount = 0 // Reset retry count on success
        
        // Schedule next poll
        this.pollTimer = setTimeout(poll, this.pollInterval)
      } catch (error) {
        console.error("Polling error:", error)
        this.retryCount++
        
        if (this.retryCount >= this.maxRetries) {
          console.log(`Max retries (${this.maxRetries}) reached`)
          this.setStatus("error")
          return
        }
        
        // Retry with exponential backoff
        const backoffDelay = Math.min(this.pollInterval * Math.pow(2, this.retryCount), 10000)
        this.pollTimer = setTimeout(poll, backoffDelay)
      }
    }

    // Start the first poll immediately
    await poll()
  }

  private async fetchDeviceStatus(): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/device_status/`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      console.log("Device status received:", data)
      
      // Format the data to match the WebSocket format expected by the device status indicator
      const formattedData = {
        type: "device_status_update",
        data: data
      }
      
      // Notify handlers with the formatted device status data
      this.notifyMessageHandlers("device_status_update", formattedData)
      
    } catch (error) {
      console.error("Failed to fetch device status:", error)
      throw error
    }
  }

  private async fetchDeviceData(): Promise<void> {
    const devices = ["lcu", "dcu", "sdu"]
    let individualEndpointsAvailable = false
    
    for (const device of devices) {
      try {
        // Try to get the latest data for each device
        const response = await fetch(`${this.baseUrl}/device_data/${device}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        })

        if (response.ok) {
          const data = await response.json()
          this.deviceData[device] = data
          
          // Notify handlers with individual device data
          this.notifyMessageHandlers(`${device}_data`, data)
          individualEndpointsAvailable = true
        } else if (response.status === 404) {
          // Device data endpoint not available, skip silently
          console.debug(`Device data endpoint not available for ${device}`)
        }
      } catch (error) {
        // Silently fail for individual device data - it's optional
        console.debug(`Failed to fetch ${device} data:`, error)
      }
    }
    
    // If individual endpoints aren't available, try the bulk endpoint
    if (!individualEndpointsAvailable) {
      try {
        const response = await fetch(`${this.baseUrl}/device_data/`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        })

        if (response.ok) {
          const data = await response.json()
          if (data.devices) {
            Object.entries(data.devices).forEach(([device, deviceData]) => {
              this.deviceData[device] = deviceData
              this.notifyMessageHandlers(`${device}_data`, { data: deviceData })
            })
          }
        }
      } catch (error) {
        console.debug("Failed to fetch bulk device data:", error)
      }
    }
  }

  private notifyMessageHandlers(type: string, data: Record<string, unknown>) {
    const handlers = this.messageHandlers.get(type)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data)
        } catch (error) {
          console.error(`Error in message handler for type '${type}':`, error)
        }
      })
    }
  }
}

// Create and export a singleton instance
export const polling = new PollingManager({
  baseUrl: 'http://192.168.2.1:8000',
  pollInterval: 2000, // Poll every 2 seconds
  maxRetries: 5,
})

// Export for compatibility with WebSocket interface
export const websocket = polling 