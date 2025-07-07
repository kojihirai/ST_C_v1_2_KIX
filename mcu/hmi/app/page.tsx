"use client"

import ControlPanel from "@/components/control-system/control-panel"
import { WebSocketStatusIndicator } from "@/components/control-system/websocket-status"
import { DeviceStatusIndicator } from "@/components/control-system/device-status-indicator"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Activity } from "lucide-react"
import { useControlSystem } from "@/hooks/useControlSystem"

export default function ControlSystemMinimal() {
  const {
    systemStatus,
    lcuDirection,
    setLcuDirection,
    dcuDirection,
    setDcuDirection,
    lcuTarget,
    setLcuTarget,
    dcuTarget,
    setDcuTarget,
    startManual,
    stopManual,
    executeCommand
  } = useControlSystem()



  return (
    <div className="flex flex-col min-h-screen bg-background p-3 pb-16">
      <div className="container mx-auto">
        <div
          className={`mb-4 p-3 rounded-lg flex items-center justify-between ${
            systemStatus === "running"
              ? "bg-green-100 dark:bg-green-900/20 border border-green-300 dark:border-green-700"
              : "bg-gray-100 dark:bg-gray-800/50 border border-gray-300 dark:border-gray-700"
          }`}
        >
          <div className="flex items-center gap-2">
            <Activity
              className={`w-5 h-5 ${
                systemStatus === "running"
                  ? "text-green-600 dark:text-green-400"
                  : "text-gray-500 dark:text-gray-400"
              }`}
            />
            <span className="font-medium text-sm">
              System Status: {systemStatus === "running" ? "RUNNING" : "STOPPED"}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <WebSocketStatusIndicator />
            <Badge variant="default" className="px-2 py-0.5 text-xs">
              Manual Mode
            </Badge>
          </div>
        </div>

        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold">SANDTROUT SYSTEM v1</h1>
          </div>
          <div className="flex gap-3">
            <Button
              onClick={systemStatus === "running" ? stopManual : startManual}
              className={`h-9 px-3 text-sm ${
                systemStatus === "running"
                  ? "bg-destructive hover:bg-destructive/90 text-destructive-foreground"
                  : "bg-green-600 hover:bg-green-700"
              }`}
            >
              {systemStatus === "running" ? "STOP MANUAL" : "START MANUAL"}
            </Button>
          </div>
        </div>

        <div className="mb-4 grid grid-cols-1 gap-4">
          <div className="flex items-start justify-between gap-4">
            <div className="w-3/4">
              <div className="flex items-center gap-3">
                <Badge variant={systemStatus === "running" ? "default" : "outline"} className="px-2 py-0.5 text-xs">
                  Status: {systemStatus === "running" ? "🟢 Running" : "⚪ Stopped"}
                </Badge>
              </div>
            </div>
          </div>
        </div>

        <ControlPanel
          lcuDirection={lcuDirection}
          setLcuDirection={setLcuDirection}
          dcuDirection={dcuDirection}
          setDcuDirection={setDcuDirection}
          lcuTarget={lcuTarget}
          setLcuTarget={setLcuTarget}
          dcuTarget={dcuTarget}
          setDcuTarget={setDcuTarget}
          executeCommand={executeCommand}
          executeOnChange={systemStatus === "running"}
        />
      </div>
      
      <DeviceStatusIndicator />
    </div>
  )
}
