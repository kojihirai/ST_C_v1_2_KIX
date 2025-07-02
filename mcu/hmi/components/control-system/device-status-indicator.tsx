"use client"

import { useEffect, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Activity, AlertCircle, WifiOff } from "lucide-react"
import { websocket } from "@/lib/websocket"

interface DeviceStatus {
  status: "connected" | "disconnected" | "error"
  last_seen: string | null
  error: string | null
}

interface DeviceStatusData {
  devices: {
    lcu: DeviceStatus
    dcu: DeviceStatus
    sdu: DeviceStatus
  }
  timestamp: string
}

export function DeviceStatusIndicator() {
  const [deviceStatus, setDeviceStatus] = useState<DeviceStatusData["devices"]>({
    lcu: { status: "disconnected", last_seen: null, error: null },
    dcu: { status: "disconnected", last_seen: null, error: null },
    sdu: { status: "disconnected", last_seen: null, error: null }
  })

  useEffect(() => {
    // Handle device status updates
    const handleDeviceStatus = (data: Record<string, unknown>) => {
      if (data.devices && data.timestamp) {
        setDeviceStatus(data.devices as DeviceStatusData["devices"])
      }
    }

    websocket.on("device_status", handleDeviceStatus)

    // Connect to WebSocket
    websocket.connect()

    return () => {
      websocket.off("device_status", handleDeviceStatus)
    }
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case "connected":
        return "bg-green-500 hover:bg-green-600"
      case "error":
        return "bg-red-500 hover:bg-red-600"
      case "disconnected":
      default:
        return "bg-gray-500 hover:bg-gray-600"
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "connected":
        return <Activity className="w-3 h-3" />
      case "error":
        return <AlertCircle className="w-3 h-3" />
      case "disconnected":
      default:
        return <WifiOff className="w-3 h-3" />
    }
  }

  const getLastSeenText = (lastSeen: string | null) => {
    if (!lastSeen) return "Never"
    
    const lastSeenDate = new Date(lastSeen)
    const now = new Date()
    const diffMs = now.getTime() - lastSeenDate.getTime()
    const diffSeconds = Math.floor(diffMs / 1000)
    
    if (diffSeconds < 60) {
      return `${diffSeconds}s ago`
    } else if (diffSeconds < 3600) {
      return `${Math.floor(diffSeconds / 60)}m ago`
    } else {
      return `${Math.floor(diffSeconds / 3600)}h ago`
    }
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 device-status-indicator border-t border-border p-2 z-50">
      <div className="container mx-auto">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium text-muted-foreground">Device Status:</span>
            {Object.entries(deviceStatus).map(([device, status]) => (
              <div key={device} className="flex items-center gap-2">
                <Badge 
                  variant="secondary" 
                  className={`device-status-badge ${status.status} ${getStatusColor(status.status)} text-white text-xs px-2 py-1 h-6 flex items-center gap-1`}
                  title={status.error || `Last seen: ${getLastSeenText(status.last_seen)}`}
                >
                  {getStatusIcon(status.status)}
                  {device.toUpperCase()}
                </Badge>
              </div>
            ))}
          </div>
          <div className="text-xs text-muted-foreground">
            Last Update: {deviceStatus.lcu.last_seen ? getLastSeenText(deviceStatus.lcu.last_seen) : "Never"}
          </div>
        </div>
      </div>
    </div>
  )
} 