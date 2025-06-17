"use client"

import React, { useState } from 'react'
import { Card } from "@/components/ui/card"
import ModeSelector from '@/components/control-system/mode-selector'
import ControlPanel from '@/components/control-system/control-panel'
import ExperimentSelector from '@/components/control-system/experiment-selector'
import { WebSocketStatusIndicator } from '@/components/control-system/websocket-status'
import { LcuDirection, DcuDirection, LcuCommand, DcuCommand, SystemMode, SystemStatus } from "@/lib/constants"
import { Experiment } from "@/lib/api-client"

export default function ControlSystemPage() {
  const [mode, setMode] = useState<SystemMode>('manual')
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null)
  const [experiments] = useState<Experiment[]>([])
  const [selectedExperimentId, setSelectedExperimentId] = useState<number | null>(null)
  const [experimentMetadata] = useState<Experiment | null>(null)
  const [systemStatus] = useState<SystemStatus>('stopped')

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
        <Card className="p-4">
          <ModeSelector mode={mode} setMode={setMode} />
        </Card>

        {mode === 'experiment' && (
          <Card className="p-4">
            <ExperimentSelector
              mode={mode}
              setMode={setMode}
              projects={[]}
              selectedProjectId={selectedProjectId}
              setSelectedProjectId={setSelectedProjectId}
              experiments={experiments}
              selectedExperimentId={selectedExperimentId}
              setSelectedExperimentId={setSelectedExperimentId}
              experimentMetadata={experimentMetadata}
              systemStatus={systemStatus}
            />
          </Card>
        )}

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
          mode={mode}
          selectedProject={experimentMetadata ? {
            project_id: experimentMetadata.project_id,
            project_name: "",
            project_description: "",
            project_params: {},
            project_controls: {},
            experiment_count: 0,
            project_created_at: "",
            project_modified_at: ""
          } : null}
        />
      </div>
    </div>
  )
} 