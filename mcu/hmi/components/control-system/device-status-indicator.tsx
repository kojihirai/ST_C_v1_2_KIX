"use client"

import { useEffect, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Activity, WifiOff, Clock } from "lucide-react"
import { websocket } from "@/lib/websocket"

interface DeviceStatus {
  device: string
  status: "online" | "warning" | "offline"
  last_seen: string | null
  heartbeat_interval: number | null
  data_count: number
}

interface DeviceStatusData {
  devices: DeviceStatus[]
  timestamp: string
}

export function DeviceStatusIndicator() {
  const [deviceStatus, setDeviceStatus] = useState<Record<string, DeviceStatus>>({
    lcu: { device: "lcu", status: "offline", last_seen: null, heartbeat_interval: null, data_count: 0 },
    dcu: { device: "dcu", status: "offline", last_seen: null, heartbeat_interval: null, data_count: 0 },
    sdu: { device: "sdu", status: "offline", last_seen: null, heartbeat_interval: null, data_count: 0 }
  })

  useEffect(() => {
    // Handle device status updates from the new monitoring system
    const handleDeviceStatusUpdate = (data: Record<string, unknown>) => {
      if (data.type === "device_status_update" && data.data) {
        const statusData = data.data as DeviceStatusData
        if (statusData.devices && Array.isArray(statusData.devices)) {
          const newStatus: Record<string, DeviceStatus> = {}
          statusData.devices.forEach((device: DeviceStatus) => {
            newStatus[device.device] = device
          })
          setDeviceStatus(newStatus)
        }
      }
    }

    // Handle legacy device status format (fallback)
    const handleLegacyDeviceStatus = (data: Record<string, unknown>) => {
      if (data.devices && data.timestamp) {
        // Convert legacy format to new format
        const legacyDevices = data.devices as Record<string, { status: string; last_seen: string | null }>
        const newStatus: Record<string, DeviceStatus> = {}
        
        Object.entries(legacyDevices).forEach(([device, status]) => {
          newStatus[device] = {
            device,
            status: status.status === "connected" ? "online" : 
                   status.status === "error" ? "warning" : "offline",
            last_seen: status.last_seen,
            heartbeat_interval: null,
            data_count: 0
          }
        })
        setDeviceStatus(newStatus)
      }
    }

    // Listen for the new device status update format
    websocket.on("device_status_update", handleDeviceStatusUpdate)
    
    // Listen for legacy format as fallback
    websocket.on("device_status", handleLegacyDeviceStatus)

    // Connect to WebSocket
    websocket.connect()

    // Request initial status
    setTimeout(() => {
      websocket.send({ type: "request_status" })
    }, 1000)

    return () => {
      websocket.off("device_status_update", handleDeviceStatusUpdate)
      websocket.off("device_status", handleLegacyDeviceStatus)
    }
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case "online":
        return "bg-green-500 hover:bg-green-600"
      case "warning":
        return "bg-yellow-500 hover:bg-yellow-600"
      case "offline":
      default:
        return "bg-gray-500 hover:bg-gray-600"
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "online":
        return <Activity className="w-3 h-3" />
      case "warning":
        return <Clock className="w-3 h-3" />
      case "offline":
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

  const getStatusTooltip = (device: DeviceStatus) => {
    const parts = []
    
    if (device.last_seen) {
      parts.push(`Last seen: ${getLastSeenText(device.last_seen)}`)
    }
    
    if (device.heartbeat_interval) {
      parts.push(`Heartbeat: ${device.heartbeat_interval}s`)
    }
    
    parts.push(`Data count: ${device.data_count}`)
    
    return parts.join(" | ")
  }

  const getOverallStatus = () => {
    const statuses = Object.values(deviceStatus)
    const onlineCount = statuses.filter(s => s.status === "online").length
    const warningCount = statuses.filter(s => s.status === "warning").length
    const offlineCount = statuses.filter(s => s.status === "offline").length
    
    if (onlineCount === statuses.length) return "All Online"
    if (offlineCount === statuses.length) return "All Offline"
    if (warningCount > 0) return `${warningCount} Warning${warningCount > 1 ? 's' : ''}`
    return `${onlineCount}/${statuses.length} Online`
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 device-status-indicator border-t border-border p-2 z-50 bg-background/95 backdrop-blur-sm">
      <div className="container mx-auto">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium text-muted-foreground">Device Status:</span>
            {Object.entries(deviceStatus).map(([device, status]) => (
              <div key={device} className="flex items-center gap-2">
                <Badge 
                  variant="secondary" 
                  className={`device-status-badge ${status.status} ${getStatusColor(status.status)} text-white text-xs px-2 py-1 h-6 flex items-center gap-1 transition-colors duration-200`}
                  title={getStatusTooltip(status)}
                >
                  {getStatusIcon(status.status)}
                  {device.toUpperCase()}
                  {status.data_count > 0 && (
                    <span className="ml-1 text-xs opacity-75">({status.data_count})</span>
                  )}
                </Badge>
              </div>
            ))}
          </div>
          <div className="text-xs text-muted-foreground">
            {getOverallStatus()}
          </div>
        </div>
      </div>
    </div>
  )
} 