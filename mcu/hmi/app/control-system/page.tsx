"use client"

import React, { useState } from 'react'
import { Card } from "@/components/ui/card"
import ControlPanel from '@/components/control-system/control-panel'
import { WebSocketStatusIndicator } from '@/components/control-system/websocket-status'
import { LcuDirection, DcuDirection, LcuCommand, DcuCommand } from "@/lib/constants"

export default function ControlSystemPage() {
  const [lcuDirection, setLcuDirection] = useState<LcuDirection>(LcuDirection.fw)
  const [lcuTarget, setLcuTarget] = useState(0)

  const [dcuDirection, setDcuDirection] = useState<DcuDirection>(DcuDirection.cw)
  const [dcuTarget, setDcuTarget] = useState(0)

  const executeCommand = (unit: "lcu" | "dcu", command: LcuCommand | DcuCommand, params: Record<string, number | string>) => {
    console.log(`Executing ${unit} command:`, command, params)
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