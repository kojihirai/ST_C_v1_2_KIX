"use client"

import ExperimentSelector from "@/components/control-system/experiment-selector"
import ControlPanel from "@/components/control-system/control-panel"
import { WebSocketStatusIndicator } from "@/components/control-system/websocket-status"
import { DeviceStatusIndicator } from "@/components/control-system/device-status-indicator"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { AlertCircle, Activity, Settings } from "lucide-react"
import { useControlSystem } from "@/hooks/useControlSystem"
import { LcuCommand, DcuCommand } from "@/lib/constants"

export default function ControlSystemMinimal() {
  const {
    mode,
    setMode,
    systemStatus,
    selectedExperiment,
    setSelectedExperiment,
    experimentMetadata,
    lcuDirection,
    setLcuDirection,
    dcuDirection,
    setDcuDirection,
    lcuTarget,
    setLcuTarget,
    dcuTarget,
    setDcuTarget,
    emergencyStop,
    startExperiment,
    stopExperiment,
    startManual,
    stopManual,
    executeCommand,
    projects,
    selectedProjectId,
    setSelectedProjectId,
    experiments
  } = useControlSystem()

  const handleReset = async () => {
    try {
      // Send homing command to LCU
      await executeCommand("lcu", LcuCommand.homing, {});
    } catch (error) {
      console.error('Error sending homing command:', error);
    }
  };

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
            <Button onClick={emergencyStop} variant="destructive" className="gap-2 emergency-pulse h-8 px-2 text-xs">
              <AlertCircle className="w-3 h-3" />
              Emergency Stop
            </Button>
            <Badge variant={mode === "manual" ? "default" : "outline"} className="px-2 py-0.5 text-xs">
              {mode === "manual" ? "Manual Mode" : mode === "experiment" ? "Experiment Mode" : "Program Mode"}
            </Badge>
          </div>
        </div>

        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold">SANDTROUT SYSTEM v1</h1>
          </div>
          <div className="flex gap-3">
            {mode === "manual" && (
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
            )}
            {mode === "experiment" && selectedExperiment && (
              <Button
                onClick={systemStatus === "running" ? stopExperiment : startExperiment}
                className={`h-9 px-3 text-sm ${
                  systemStatus === "running"
                    ? "bg-destructive hover:bg-destructive/90 text-destructive-foreground"
                    : "bg-green-600 hover:bg-green-700"
                }`}
              >
                {systemStatus === "running" ? "STOP EXPERIMENT" : "START EXPERIMENT"}
              </Button>
            )}
          </div>
        </div>

        <div className="mb-4 grid grid-cols-1 gap-4">
          <div className="flex items-start justify-between gap-4">
            <div className="w-3/4">
              <ExperimentSelector
                mode={mode}
                setMode={setMode}
                projects={projects}
                selectedProjectId={selectedProjectId}
                setSelectedProjectId={setSelectedProjectId}
                experiments={experiments}
                selectedExperimentId={selectedExperiment}
                setSelectedExperimentId={setSelectedExperiment}
                experimentMetadata={experimentMetadata}
                systemStatus={systemStatus}
                onReset={handleReset}
              />
            </div>

            <div className="flex items-center gap-3 mt-7">
              {mode === "experiment" && selectedExperiment && (
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1"
                  onClick={() => window.location.href = "/control-system/manage"}
                >
                  <Settings className="h-4 w-4" />
                  Manage
                </Button>
              )}
              <Badge variant={systemStatus === "running" ? "default" : "outline"} className="px-2 py-0.5 text-xs">
                Status: {systemStatus === "running" ? "🟢 Running" : "⚪ Stopped"}
              </Badge>
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
          executeCommand={executeCommand as (unit: "lcu" | "dcu", command: LcuCommand | DcuCommand, params: Record<string, number | string>) => Promise<void>}
          executeOnChange={mode === "manual" ? systemStatus === "running" : systemStatus === "running" && selectedExperiment !== null}
          mode={mode}
          selectedProject={projects.find(p => p.project_id === selectedProjectId)}
        />
      </div>
      
      <DeviceStatusIndicator />
    </div>
  )
}
