"use client"

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"

interface Parameter {
  name: string;
  value: string | number;
  description?: string;
  units?: string;
}

interface ProjectParametersTableProps {
  constants?: Array<Parameter>
  independent?: Array<Parameter>
  dependent?: Array<Parameter>
  general?: Array<Parameter>
  controls?: {
    drill?: { setpoint: number; direction: string }
    linearActuator?: { setpoint: number; direction: string }
  }
}

export function ProjectParametersTable({
  constants = [],
  independent = [],
  dependent = [],
  general = [],
  controls = {}
}: ProjectParametersTableProps) {
  // Helper function to render a parameter table
  const ParameterTable = ({ parameters, title, isDependent = false, isIndependent = false }: { parameters: Array<Parameter>, title: string, isDependent?: boolean, isIndependent?: boolean }) => {
    if (parameters.length === 0) {
      return <p className="text-muted-foreground">No {title.toLowerCase()} defined</p>
    }

    return (
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Parameter</TableHead>
            {!isDependent && !isIndependent && <TableHead>Value</TableHead>}
            <TableHead>Description</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {parameters.map((param) => (
            <TableRow key={param.name}>
              <TableCell className="font-medium">{param.name}</TableCell>
              {!isDependent && !isIndependent && <TableCell>{param.value} {param.units ? `(${param.units})` : ''}</TableCell>}
              <TableCell>{param.description || ''}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    )
  }

  // Helper function to get direction display text
  const getDirectionDisplay = (direction: string, type: 'drill' | 'linear') => {
    if (type === 'drill') {
      return direction === 'cw' ? 'Clockwise (CW)' : 'Counter-clockwise (CCW)'
    } else {
      return direction === 'fw' ? 'Forward (FW)' : 'Backward (BW)'
    }
  }

  // Helper function to get direction badge variant
  const getDirectionBadgeVariant = (direction: string, currentDirection: string) => {
    return direction === currentDirection ? 'default' : 'outline'
  }

  return (
    <Card className="mb-6">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">Project Parameters</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="general" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="general">General</TabsTrigger>
            <TabsTrigger value="parameters">Parameters</TabsTrigger>
            <TabsTrigger value="controls">Controls</TabsTrigger>
          </TabsList>
          
          <TabsContent value="general">
            <ParameterTable parameters={general} title="General Parameters" />
          </TabsContent>
          
          <TabsContent value="parameters">
            <Tabs defaultValue="constants" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="constants">Constants</TabsTrigger>
                <TabsTrigger value="independent">Independent Variables</TabsTrigger>
                <TabsTrigger value="dependent">Dependent Variables</TabsTrigger>
              </TabsList>
              
              <TabsContent value="constants">
                <ParameterTable parameters={constants} title="Constants" />
              </TabsContent>
              
              <TabsContent value="independent">
                <ParameterTable parameters={independent} title="Independent Variables" isIndependent={true} />
              </TabsContent>
              
              <TabsContent value="dependent">
                <ParameterTable parameters={dependent} title="Dependent Variables" isDependent={true} />
              </TabsContent>
            </Tabs>
          </TabsContent>
          
          <TabsContent value="controls">
            <Tabs defaultValue="drill" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="drill">Drill</TabsTrigger>
                <TabsTrigger value="linear">Linear Actuator</TabsTrigger>
              </TabsList>
              
              <TabsContent value="drill">
                <div className="p-4 border rounded-md">
                  <h3 className="text-sm font-medium mb-4">Drill Control</h3>
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-xs font-medium mb-1">Setpoint (V)</h4>
                      <div className="flex items-center gap-2">
                        <input 
                          type="range" 
                          min="0" 
                          max="24" 
                          step="0.1"
                          value={controls.drill?.setpoint || 0} 
                          className="w-full"
                          readOnly
                        />
                        <span className="text-sm">{controls.drill?.setpoint || 0}V</span>
                      </div>
                    </div>
                    <div>
                      <h4 className="text-xs font-medium mb-1">Direction</h4>
                      <div className="flex gap-2">
                        <Badge variant={getDirectionBadgeVariant('cw', controls.drill?.direction || '')}>
                          {getDirectionDisplay('cw', 'drill')}
                        </Badge>
                        <Badge variant={getDirectionBadgeVariant('ccw', controls.drill?.direction || '')}>
                          {getDirectionDisplay('ccw', 'drill')}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="linear">
                <div className="p-4 border rounded-md">
                  <h3 className="text-sm font-medium mb-4">Linear Actuator Control</h3>
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-xs font-medium mb-1">Setpoint (mm)</h4>
                      <div className="flex items-center gap-2">
                        <input 
                          type="range" 
                          min="0" 
                          max="100" 
                          value={controls.linearActuator?.setpoint || 0} 
                          className="w-full"
                          readOnly
                        />
                        <span className="text-sm">{controls.linearActuator?.setpoint || 0}mm</span>
                      </div>
                    </div>
                    <div>
                      <h4 className="text-xs font-medium mb-1">Direction</h4>
                      <div className="flex gap-2">
                        <Badge variant={getDirectionBadgeVariant('fw', controls.linearActuator?.direction || '')}>
                          {getDirectionDisplay('fw', 'linear')}
                        </Badge>
                        <Badge variant={getDirectionBadgeVariant('bw', controls.linearActuator?.direction || '')}>
                          {getDirectionDisplay('bw', 'linear')}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
