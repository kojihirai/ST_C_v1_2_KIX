"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Square } from 'lucide-react'
import LcuControlTab from "./lcu-control-tab"
import DcuControlTab from "./dcu-control-tab"
import { LcuDirection, DcuDirection, LcuCommand, DcuCommand } from "@/lib/constants"
import { Project } from "@/lib/api-client"
import React from "react"

interface ControlPanelProps {
  lcuDirection: LcuDirection
  setLcuDirection: (direction: LcuDirection) => void
  dcuDirection: DcuDirection
  setDcuDirection: (direction: DcuDirection) => void
  lcuTarget: number
  setLcuTarget: (target: number) => void
  dcuTarget: number
  setDcuTarget: (target: number) => void
  executeCommand: (unit: "lcu" | "dcu", command: LcuCommand | DcuCommand, params: Record<string, number | string>) => void
  executeOnChange?: boolean
  mode: "manual" | "experiment" | "program"
  selectedProject?: Project | null
}

export default function ControlPanel({
  lcuDirection,
  setLcuDirection,
  dcuDirection,
  setDcuDirection,
  lcuTarget,
  setLcuTarget,
  dcuTarget,
  setDcuTarget,
  executeCommand,
  executeOnChange = false,
  mode,
  selectedProject
}: ControlPanelProps) {
  // Track last sent command values
  const [lastLcuCommand, setLastLcuCommand] = React.useState<{direction: LcuDirection, target: number} | null>(null);
  const [lastDcuCommand, setLastDcuCommand] = React.useState<{direction: DcuDirection, target: number} | null>(null);

  const executeLcuCommand = () => {
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
    executeCommand("lcu", command, params)
    setLastLcuCommand({ direction: lcuDirection, target: lcuTarget })
  }

  const executeDcuCommand = () => {
    // Only send command if values have changed
    if (lastDcuCommand?.direction === dcuDirection && lastDcuCommand?.target === dcuTarget) {
      return;
    }

    let params: Record<string, number | string> = {}
    let command: DcuCommand = DcuCommand.idle

    // Simplified command logic - just use run_cont for all active commands
    if (dcuTarget > 0) {
      command = DcuCommand.run_cont
      params = { target: dcuTarget, direction: dcuDirection }
    } else {
      command = DcuCommand.idle
    }

    executeCommand("dcu", command, params)
    setLastDcuCommand({ direction: dcuDirection, target: dcuTarget })
  }

  const stopLcu = () => {
    executeCommand("lcu", LcuCommand.idle, {})
  }

  const stopDcu = () => {
    executeCommand("dcu", DcuCommand.idle, {})
  }

  // Get project control values if in experiment mode
  const projectControls = mode === "experiment" && selectedProject?.project_controls ? {
    lcu: selectedProject.project_controls.linearActuator,
    dcu: selectedProject.project_controls.drill
  } : null

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* LCU Controls */}
      <Card className="shadow-sm">
        <CardHeader className="py-2 px-3 flex flex-row justify-between items-center">
          <CardTitle className="text-sm">Linear Actuator Controls</CardTitle>
          <Button variant="outline" className="h-8 px-2 text-xs" onClick={stopLcu}>
            <Square className="w-3 h-3 mr-1 fill-current" />
            Stop
          </Button>
        </CardHeader>
        <CardContent className="p-3">
          <LcuControlTab
            lcuDirection={lcuDirection}
            setLcuDirection={setLcuDirection}
            lcuTarget={mode === "experiment" && projectControls?.lcu && typeof projectControls.lcu === 'object' && 'setpoint' in projectControls.lcu 
              ? Number(projectControls.lcu.setpoint) 
              : lcuTarget}
            setLcuTarget={setLcuTarget}
            executeLcuCommand={executeLcuCommand}
            executeOnChange={executeOnChange && mode === "manual"}
            isReadOnly={mode === "experiment"}
            projectDirection={mode === "experiment" && projectControls?.lcu && typeof projectControls.lcu === 'object' && 'direction' in projectControls.lcu 
              ? projectControls.lcu.direction as string 
              : undefined}
          />
        </CardContent>
      </Card>

      {/* DCU Controls */}
      <Card className="shadow-sm">
        <CardHeader className="py-2 px-3 flex flex-row justify-between items-center">
          <CardTitle className="text-sm">Drill Controls</CardTitle>
          <Button variant="outline" className="h-8 px-2 text-xs" onClick={stopDcu}>
            <Square className="w-3 h-3 mr-1 fill-current" />
            Stop
          </Button>
        </CardHeader>
        <CardContent className="p-3">
          <DcuControlTab
            dcuDirection={dcuDirection}
            setDcuDirection={setDcuDirection}
            dcuTarget={mode === "experiment" && projectControls?.dcu && typeof projectControls.dcu === 'object' && 'setpoint' in projectControls.dcu 
              ? Number(projectControls.dcu.setpoint) 
              : dcuTarget}
            setDcuTarget={setDcuTarget}
            executeDcuCommand={executeDcuCommand}
            executeOnChange={executeOnChange && mode === "manual"}
            isReadOnly={mode === "experiment"}
            projectDirection={mode === "experiment" && projectControls?.dcu && typeof projectControls.dcu === 'object' && 'direction' in projectControls.dcu 
              ? projectControls.dcu.direction as DcuDirection 
              : undefined}
          />
        </CardContent>
      </Card>
    </div>
  )
}
