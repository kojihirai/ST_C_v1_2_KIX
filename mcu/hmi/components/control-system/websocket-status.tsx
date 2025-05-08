"use client"

import { useEffect, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Wifi, WifiOff } from "lucide-react"
import { websocket, type WebSocketStatus } from "@/lib/websocket"

export function WebSocketStatusIndicator() {
  const [status, setStatus] = useState<WebSocketStatus>("disconnected")

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
          Connected
        </>
      ) : status === "connecting" ? (
        <>
          <Wifi className="w-4 h-4 animate-pulse" />
          Connecting...
        </>
      ) : status === "error" ? (
        <>
          <WifiOff className="w-4 h-4" />
          Connection Error
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

