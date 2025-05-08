"use client"

import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { SystemMode, SystemStatus } from "@/lib/constants"
import { Project, Experiment } from "@/lib/api-client"
import { ExperimentParametersTable } from "@/components/experiment-parameters-table"
import { Button } from "@/components/ui/button"
import { RotateCcw } from "lucide-react"
import { useState } from "react"

// Define a type for the experiment metadata
interface ExperimentMetadataWithVariables extends Experiment {
  variables?: Record<string, unknown>;
  controls?: Record<string, unknown>;
}

interface ExperimentSelectorProps {
  mode: SystemMode
  setMode: (mode: SystemMode) => void
  projects: Project[]
  selectedProjectId: number | null
  setSelectedProjectId: (id: number) => void
  experiments: Experiment[]
  selectedExperimentId: number | null
  setSelectedExperimentId: (id: number) => void
  experimentMetadata: ExperimentMetadataWithVariables | null
  systemStatus: SystemStatus
  onReset?: () => void
}

export default function ExperimentSelector({
  mode,
  setMode,
  projects,
  selectedProjectId,
  setSelectedProjectId,
  experiments,
  selectedExperimentId,
  setSelectedExperimentId,
  experimentMetadata,
  systemStatus,
  onReset,
}: ExperimentSelectorProps) {
  const [isResetting, setIsResetting] = useState(false);
  
  // Get the selected project and its parameters
  const selectedProject = projects.find(p => p.project_id === selectedProjectId);
  const projectParams = selectedProject?.project_params || {};
  
  // Get independent variables from project params and experiment metadata
  const independentVariables = Array.isArray(projectParams.independent) 
    ? projectParams.independent.map((variable: { name: string; value?: number; description?: string; units?: string }) => ({
        name: variable.name,
        value: typeof experimentMetadata?.variables?.[variable.name] === 'number' 
          ? experimentMetadata.variables[variable.name] as number 
          : (variable.value ?? 0),
        description: variable.description || '',
        units: variable.units || ''
      }))
    : [];

  // Handle reset button click
  const handleReset = async () => {
    if (!selectedProjectId || !selectedExperimentId) return;
    
    try {
      setIsResetting(true);
      
      // Call the onReset callback if provided
      if (onReset) {
        onReset();
      }
      
      console.log('Experiment reset successfully');
    } catch (error) {
      console.error('Error resetting experiment:', error);
    } finally {
      setIsResetting(false);
    }
  };

  // Log for debugging
  console.log('ExperimentSelector - project params:', projectParams);
  console.log('ExperimentSelector - experiment metadata:', experimentMetadata);
  console.log('ExperimentSelector - independent variables:', independentVariables);

  return (
    <div className="w-full">
      {/* Mode Selector and Dropdowns Row */}
      <div className="mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Mode Selector */}
          <div className="w-full md:w-2/5">
            <Label className="text-sm font-medium mb-2 block">Mode</Label>
            <Tabs 
              value={mode} 
              onValueChange={(value) => setMode(value as SystemMode)} 
              className="w-full"
            >
              <TabsList className="grid grid-cols-2">
                <TabsTrigger 
                  value="manual" 
                  className="text-sm"
                  disabled={systemStatus === "running"}
                >
                  Manual
                </TabsTrigger>
                <TabsTrigger 
                  value="experiment" 
                  className="text-sm"
                  disabled={systemStatus === "running"}
                >
                  Experiment
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          {mode === "experiment" && (
            <div className="w-full md:w-3/5 flex flex-row justify-end gap-4">
              {/* Project Dropdown */}
              <div className="w-[46%]">
                <Label className="text-sm font-medium mb-2 block">Project</Label>
                <Select
                  value={selectedProjectId?.toString()}
                  onValueChange={(value) => setSelectedProjectId(Number.parseInt(value))}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select project" />
                  </SelectTrigger>
                  <SelectContent>
                    {projects.map((project) => (
                      <SelectItem key={project.project_id} value={project.project_id.toString()}>
                        {project.project_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Experiment Dropdown */}
              <div className="w-[46%]">
                <Label className="text-sm font-medium mb-2 block">Experiment</Label>
                <Select
                  value={selectedExperimentId?.toString()}
                  onValueChange={(value) => setSelectedExperimentId(Number.parseInt(value))}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select experiment" />
                  </SelectTrigger>
                  <SelectContent>
                    {experiments.map((exp) => (
                      <SelectItem key={exp.experiment_id} value={exp.experiment_id.toString()}>
                        {exp.experiment_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Project and Experiment Parameters */}
      {mode === "experiment" && selectedProject && (
        <Card className="w-full">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg font-semibold">Parameters</CardTitle>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleReset}
              className="flex items-center gap-1 bg-yellow-500 hover:bg-yellow-600 text-white border-yellow-600"
              disabled={systemStatus === "running" || isResetting || !selectedProjectId || !selectedExperimentId}
            >
              <RotateCcw className={`h-4 w-4 ${isResetting ? 'animate-spin' : ''}`} />
              {isResetting ? 'Resetting...' : 'Reset'}
            </Button>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="independent" className="w-full">
              <TabsList className="grid grid-cols-4 mb-4">
                <TabsTrigger value="constants">Constants</TabsTrigger>
                <TabsTrigger value="independent">Independent</TabsTrigger>
                <TabsTrigger value="dependent">Dependent</TabsTrigger>
                <TabsTrigger value="controls">Controls</TabsTrigger>
              </TabsList>
              
              {/* Constants Tab */}
              <TabsContent value="constants" className="max-h-[200px] overflow-y-auto">
                {selectedProject.project_params?.constants && 
                 Array.isArray(selectedProject.project_params.constants) && 
                 selectedProject.project_params.constants.length > 0 ? (
                  <div className="space-y-2">
                    {selectedProject.project_params.constants.map((param: { name: string; value: string | number; units?: string; description?: string }) => (
                      <div key={param.name} className="border-b pb-2">
                        <div className="flex justify-between items-baseline">
                          <span className="font-medium">{param.name}</span>
                          <span>{param.value} {param.units ? `(${param.units})` : ''}</span>
                        </div>
                        {param.description && (
                          <p className="text-xs text-muted-foreground mt-1">{param.description}</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted-foreground">No constants defined</p>
                )}
              </TabsContent>
              
              {/* Independent Variables Tab */}
              <TabsContent value="independent" className="max-h-[200px] overflow-y-auto">
                {selectedProject.project_params?.independent && 
                 Array.isArray(selectedProject.project_params.independent) && 
                 selectedProject.project_params.independent.length > 0 ? (
                  <ExperimentParametersTable 
                    parameters={experimentMetadata?.variables as Record<string, number | string | boolean> || {}}
                    independentVariables={independentVariables}
                  />
                ) : (
                  <p className="text-muted-foreground">No independent variables defined</p>
                )}
              </TabsContent>
              
              {/* Dependent Variables Tab */}
              <TabsContent value="dependent" className="max-h-[200px] overflow-y-auto">
                {selectedProject.project_params?.dependent && 
                 Array.isArray(selectedProject.project_params.dependent) && 
                 selectedProject.project_params.dependent.length > 0 ? (
                  <div className="space-y-2">
                    {selectedProject.project_params.dependent.map((param: { name: string; value: string | number; units?: string; description?: string }) => (
                      <div key={param.name} className="border-b pb-2">
                        <div className="flex justify-between items-baseline">
                          <span className="font-medium">{param.name}</span>
                          <span>{param.value} {param.units ? `(${param.units})` : ''}</span>
                        </div>
                        {param.description && (
                          <p className="text-xs text-muted-foreground mt-1">{param.description}</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted-foreground">No dependent variables defined</p>
                )}
              </TabsContent>
              
              {/* Controls Tab */}
              <TabsContent value="controls" className="max-h-[200px] overflow-y-auto">
                {selectedProject.project_controls ? (
                  <div className="flex gap-8">
                    {/* Linear Actuator Controls */}
                    {selectedProject.project_controls.linearActuator && 
                     typeof selectedProject.project_controls.linearActuator === 'object' && 
                     'setpoint' in selectedProject.project_controls.linearActuator && 
                     'direction' in selectedProject.project_controls.linearActuator && (
                      <div className="border-b pb-2">
                        <div className="font-medium mb-1">Linear Actuator</div>
                        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                        <div>Setpoint: {(selectedProject.project_controls.linearActuator as any).setpoint} mm/s</div>
                        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                        <div>Direction: {(selectedProject.project_controls.linearActuator as any).direction === "fw" ? "Forward" : "Backward"}</div>
                      </div>
                    )}
                    {/* Drill Controls */}
                    {selectedProject.project_controls.drill && 
                     typeof selectedProject.project_controls.drill === 'object' && 
                     'setpoint' in selectedProject.project_controls.drill && 
                     'direction' in selectedProject.project_controls.drill && (
                      <div className="border-b pb-2">
                        <div className="font-medium mb-1">Drill</div>
                        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                        <div>Setpoint: {(selectedProject.project_controls.drill as any).setpoint}V</div>
                        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                        <div>Direction: {(selectedProject.project_controls.drill as any).direction === "cw" ? "Clockwise" : "Counterclockwise"}</div>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-muted-foreground">No controls defined</p>
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
