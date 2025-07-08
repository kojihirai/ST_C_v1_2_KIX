"use client"

import { useEffect, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Wifi, WifiOff } from "lucide-react"
import { websocket, type PollingStatus } from "@/lib/polling-manager"

export function WebSocketStatusIndicator() {
  const [status, setStatus] = useState<PollingStatus>("disconnected")

  useEffect(() => {
    // Register for status updates
    websocket.onStatusChange(setStatus)

    // Connect to WebSocket on component mount
    websocket.connect()

    // Disconnect when component unmounts
    return () => {
      websocket.disconnect()
    }
  }, [])

  return (
    <Badge
      variant={status === "connected" ? "default" : "outline"}
      className={`text-sm py-1 px-3 h-8 flex items-center gap-2 ${
        status === "error" ? "bg-destructive text-destructive-foreground" : ""
      }`}
    >
      {status === "connected" ? (
        <>
          <Wifi className="w-4 h-4" />
          Polling
        </>
      ) : status === "connecting" ? (
        <>
          <Wifi className="w-4 h-4 animate-pulse" />
          Starting...
        </>
      ) : status === "error" ? (
        <>
          <WifiOff className="w-4 h-4" />
          Polling Error
        </>
      ) : (
        <>
          <WifiOff className="w-4 h-4" />
          Disconnected
        </>
      )}
    </Badge>
  )
}

