"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Square, Play } from 'lucide-react'
import LcuControlTab from "./lcu-control-tab"
import DcuControlTab from "./dcu-control-tab"
import { LcuDirection, DcuDirection, LcuCommand, DcuCommand } from "@/lib/constants"
import React from "react"

interface ControlPanelProps {
  lcuDirection: LcuDirection
  setLcuDirection: (direction: LcuDirection) => void
  dcuDirection: DcuDirection
  setDcuDirection: (direction: DcuDirection) => void
  lcuTarget: number
  setLcuTarget: (target: number) => void
  executeCommand: (unit: "lcu" | "dcu", command: LcuCommand | DcuCommand, params: Record<string, number | string>) => void
  executeOnChange?: boolean
}

export default function ControlPanel({
  lcuDirection,
  setLcuDirection,
  dcuDirection,
  setDcuDirection,
  lcuTarget,
  setLcuTarget,
  executeCommand,
  executeOnChange = false
}: ControlPanelProps) {
  // Track last sent command values
  const [lastLcuCommand, setLastLcuCommand] = React.useState<{direction: LcuDirection, target: number} | null>(null);
  const [lastDcuCommand, setLastDcuCommand] = React.useState<{direction: DcuDirection, target: number} | null>(null);
  const [lcuStatus, setLcuStatus] = React.useState<string>("");
  const [dcuStatus, setDcuStatus] = React.useState<string>("");

  const executeLcuCommand = async () => {
    // Only send command if values have changed
    if (lastLcuCommand?.direction === lcuDirection && lastLcuCommand?.target === lcuTarget) {
      return;
    }

    let params: Record<string, number | string> = {}
    let command: LcuCommand = LcuCommand.idle

    // Simplified command logic - just use run_cont for all active commands
    if (lcuTarget > 0) {
      command = LcuCommand.run_cont
      params = { target: lcuTarget, direction: lcuDirection }
    } else {
      command = LcuCommand.idle
    }

    console.log(`Sending LCU command: ${command} with params:`, params)
    setLcuStatus("Sending...")
    
    try {
      await executeCommand("lcu", command, params)
      setLcuStatus("Sent")
      setLastLcuCommand({ direction: lcuDirection, target: lcuTarget })
      
      // Clear status after 2 seconds
      setTimeout(() => setLcuStatus(""), 2000)
    } catch (error) {
      setLcuStatus("Failed")
      console.error("LCU command failed:", error)
    }
  }

  const executeDcuCommand = async () => {
    // Only send command if values have changed
    if (lastDcuCommand?.direction === dcuDirection) {
      return;
    }

    let params: Record<string, number | string> = {}
    let command: DcuCommand = DcuCommand.idle

    // Simplified command logic - just use run_cont for ON state
    if (dcuDirection === DcuDirection.on) {
      command = DcuCommand.run_cont
      params = { direction: dcuDirection }
    } else {
      command = DcuCommand.idle
    }

    console.log(`Sending DCU command: ${command} with params:`, params)
    setDcuStatus("Sending...")
    
    try {
      await executeCommand("dcu", command, params)
      setDcuStatus("Sent")
      setLastDcuCommand({ direction: dcuDirection, target: 0 })
      
      // Clear status after 2 seconds
      setTimeout(() => setDcuStatus(""), 2000)
    } catch (error) {
      setDcuStatus("Failed")
      console.error("DCU command failed:", error)
    }
  }

  const stopLcu = async () => {
    setLcuStatus("Stopping...")
    try {
      await executeCommand("lcu", LcuCommand.idle, {})
      setLcuStatus("Stopped")
      setLastLcuCommand(null)
      setTimeout(() => setLcuStatus(""), 2000)
    } catch (error) {
      setLcuStatus("Stop failed")
      console.error("LCU stop failed:", error)
    }
  }

  const stopDcu = async () => {
    setDcuStatus("Stopping...")
    try {
      await executeCommand("dcu", DcuCommand.idle, {})
      setDcuStatus("Stopped")
      setLastDcuCommand(null)
      setTimeout(() => setDcuStatus(""), 2000)
    } catch (error) {
      setDcuStatus("Stop failed")
      console.error("DCU stop failed:", error)
    }
  }

  const resumeLcu = async () => {
    if (lastLcuCommand) {
      setLcuStatus("Resuming...")
      try {
        await executeCommand("lcu", LcuCommand.run_cont, { target: lastLcuCommand.target, direction: lastLcuCommand.direction })
        setLcuStatus("Resumed")
        setTimeout(() => setLcuStatus(""), 2000)
      } catch (error) {
        setLcuStatus("Resume failed")
        console.error("LCU resume failed:", error)
      }
    }
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* LCU Controls */}
      <Card className="shadow-sm">
        <CardHeader className="py-2 px-3 flex flex-row justify-between items-center">
          <CardTitle className="text-sm">Linear Actuator Controls</CardTitle>
          <div className="flex gap-2 items-center">
            {lcuStatus && <span className="text-xs text-gray-600">{lcuStatus}</span>}
            <Button variant="outline" className="h-8 px-2 text-xs" onClick={resumeLcu} disabled={!lastLcuCommand}>
              <Play className="w-3 h-3 mr-1" />
              Resume
            </Button>
            <Button variant="outline" className="h-8 px-2 text-xs" onClick={stopLcu}>
              <Square className="w-3 h-3 mr-1 fill-current" />
              Stop
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-3">
          <LcuControlTab
            lcuDirection={lcuDirection}
            setLcuDirection={setLcuDirection}
            lcuTarget={lcuTarget}
            setLcuTarget={setLcuTarget}
            executeLcuCommand={executeLcuCommand}
            executeOnChange={executeOnChange}
            isReadOnly={false}
          />
        </CardContent>
      </Card>

      {/* DCU Controls */}
      <Card className="shadow-sm">
        <CardHeader className="py-2 px-3 flex flex-row justify-between items-center">
          <CardTitle className="text-sm">Contactor Controls</CardTitle>
          <div className="flex gap-2 items-center">
            {dcuStatus && <span className="text-xs text-gray-600">{dcuStatus}</span>}
            <Button variant="outline" className="h-8 px-2 text-xs" onClick={stopDcu}>
              <Square className="w-3 h-3 mr-1 fill-current" />
              Stop
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-3">
          <DcuControlTab
            dcuDirection={dcuDirection}
            setDcuDirection={setDcuDirection}
            executeDcuCommand={executeDcuCommand}
            executeOnChange={executeOnChange}
            isReadOnly={false}
          />
        </CardContent>
      </Card>
    </div>
  )
}
