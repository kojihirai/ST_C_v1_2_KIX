"use client"

import { useEffect, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Activity, Gauge, Zap, Settings } from "lucide-react"
import { websocket } from "@/lib/polling-manager"

interface DeviceStatus {
  device: string
  status: "online" | "warning" | "offline"
  last_seen: string | null
  data_count: number
}

interface DeviceStatusData {
  devices: DeviceStatus[]
  timestamp: string
}

// Device-specific data interfaces
interface LcuData {
  pos_mm?: number
  current_speed?: number
  load?: number
  mode?: number
  direction?: number
  target?: number
}

interface DcuData {
  rpm?: number
  torque?: number
  mode?: number
  direction?: number
  target?: number
}

interface SduData {
  DRILL_CURRENT?: number
  POWER_CURRENT?: number
  LINEAR_CURRENT?: number
}

export function DeviceStatusIndicator() {
  const [deviceStatus, setDeviceStatus] = useState<Record<string, DeviceStatus>>({
    lcu: { device: "lcu", status: "offline", last_seen: null, data_count: 0 },
    dcu: { device: "dcu", status: "offline", last_seen: null, data_count: 0 },
    sdu: { device: "sdu", status: "offline", last_seen: null, data_count: 0 }
  })

  // Store latest device data for display
  const [deviceData, setDeviceData] = useState<Record<string, LcuData | DcuData | SduData>>({
    lcu: {},
    dcu: {},
    sdu: {}
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

    // Handle device data updates
    const handleDeviceData = (device: string, data: Record<string, unknown>) => {
      if (data.data) {
        setDeviceData(prev => ({
          ...prev,
          [device]: data.data as LcuData | DcuData | SduData
        }))
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
            data_count: 0
          }
        })
        setDeviceStatus(newStatus)
      }
    }

    // Listen for the new device status update format
    websocket.on("device_status_update", handleDeviceStatusUpdate)
    
    // Listen for individual device data updates
    websocket.on("lcu_data", (data) => handleDeviceData("lcu", data))
    websocket.on("dcu_data", (data) => handleDeviceData("dcu", data))
    websocket.on("sdu_data", (data) => handleDeviceData("sdu", data))
    
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
      websocket.off("lcu_data", () => {})
      websocket.off("dcu_data", () => {})
      websocket.off("sdu_data", () => {})
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



  const getDeviceIcon = (device: string) => {
    switch (device) {
      case "lcu":
        return <Settings className="w-3 h-3" />
      case "dcu":
        return <Gauge className="w-3 h-3" />
      case "sdu":
        return <Zap className="w-3 h-3" />
      default:
        return <Activity className="w-3 h-3" />
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

  const getDeviceDataText = (device: string, data: LcuData | DcuData | SduData) => {
    switch (device) {
      case "lcu":
        const lcuData = data as LcuData
        if (lcuData.pos_mm !== undefined && lcuData.current_speed !== undefined) {
          return `${lcuData.pos_mm.toFixed(1)}mm | ${lcuData.current_speed.toFixed(2)}mm/s`
        }
        break
      case "dcu":
        const dcuData = data as DcuData
        if (dcuData.rpm !== undefined && dcuData.torque !== undefined) {
          return `${dcuData.rpm.toFixed(1)}rpm | ${dcuData.torque.toFixed(2)}Nm`
        }
        break
      case "sdu":
        const sduData = data as SduData
        if (sduData.DRILL_CURRENT !== undefined) {
          return `${sduData.DRILL_CURRENT.toFixed(2)}A | ${sduData.POWER_CURRENT?.toFixed(2) || '0.00'}A | ${sduData.LINEAR_CURRENT?.toFixed(2) || '0.00'}A`
        }
        break
    }
    return ""
  }

  const getStatusTooltip = (device: string, status: DeviceStatus, data: LcuData | DcuData | SduData) => {
    const parts = []
    
    // Device name and status
    parts.push(`${device.toUpperCase()}: ${status.status.toUpperCase()}`)
    
    // Last seen time
    if (status.last_seen) {
      parts.push(`Last seen: ${getLastSeenText(status.last_seen)}`)
    }
    
    // Data count
    parts.push(`Data count: ${status.data_count}`)
    
    // Device-specific data
    const dataText = getDeviceDataText(device, data)
    if (dataText) {
      parts.push(`Current: ${dataText}`)
    }
    
    return parts.join("\n")
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
            {Object.entries(deviceStatus).map(([device, status]) => {
              const data = deviceData[device] || {}
              const dataText = getDeviceDataText(device, data)
              
              return (
                <div key={device} className="flex items-center gap-2">
                  <Badge 
                    variant="secondary" 
                    className={`device-status-badge ${status.status} ${getStatusColor(status.status)} text-white text-xs px-3 py-1 h-7 flex items-center gap-2 transition-colors duration-200`}
                    title={getStatusTooltip(device, status, data)}
                  >
                    {getDeviceIcon(device)}
                    <span className="font-medium">{device.toUpperCase()}</span>
                    {status.data_count > 0 && (
                      <span className="text-xs opacity-75">({status.data_count})</span>
                    )}
                  </Badge>
                  {dataText && status.status === "online" && (
                    <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
                      {dataText}
                    </span>
                  )}
                </div>
              )
            })}
          </div>
          <div className="text-xs text-muted-foreground">
            {getOverallStatus()}
          </div>
        </div>
      </div>
    </div>
  )
} 