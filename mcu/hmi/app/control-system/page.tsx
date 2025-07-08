"use client"

import React, { useState } from 'react'
import ControlPanel from '@/components/control-system/control-panel'
import { WebSocketStatusIndicator } from '@/components/control-system/websocket-status'
import { LcuDirection, DcuDirection, LcuCommand, DcuCommand } from "@/lib/constants"
import apiClient from '@/lib/api-client'

export default function ControlSystemPage() {
  const [lcuDirection, setLcuDirection] = useState<LcuDirection>(LcuDirection.fw)
  const [lcuTarget, setLcuTarget] = useState(0)

  const [dcuDirection, setDcuDirection] = useState<DcuDirection>(DcuDirection.cw)
  const [dcuTarget, setDcuTarget] = useState(0)

  const executeCommand = async (unit: "lcu" | "dcu", command: LcuCommand | DcuCommand, params: Record<string, number | string>) => {
    console.log(`Executing ${unit} command:`, command, params)
    
    try {
      // Convert command format to match firmware expectations
      const commandData = {
        mode: command,
        direction: Number(params.direction) || 0,
        target: Number(params.target) || 0
      }
      
      const response = await apiClient.sendCommand({
        device: unit,
        command: commandData
      })
      
      if (response.success) {
        console.log(`Command sent successfully to ${unit}`)
      } else {
        console.error(`Failed to send command to ${unit}:`, response.message)
      }
    } catch (error) {
      console.error(`Error sending command to ${unit}:`, error)
    }
  }

  return (
    <div className="container mx-auto py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Control System</h1>
        <WebSocketStatusIndicator />
      </div>

      <div className="space-y-6">
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
          executeOnChange={true}
        />
      </div>
    </div>
  )
} 