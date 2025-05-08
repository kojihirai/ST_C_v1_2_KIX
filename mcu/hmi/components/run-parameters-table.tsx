"use client"

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Run } from "@/lib/data"

interface RunParametersTableProps {
  runs: Run[]
}

export function RunParametersTable({ runs }: RunParametersTableProps) {
  // Parse run parameters to extract independent variables
  const parseRunParameters = (run: Run) => {
    try {
      if (!run.run_params) return { independentVars: {} }
      
      const params = typeof run.run_params === 'string' 
        ? JSON.parse(run.run_params) 
        : run.run_params
      
      // Extract independent variables (excluding control inputs)
      const independentVars = { ...params }
      delete independentVars.drillSetpoint
      delete independentVars.linearActuatorSetpoint
      
      return { independentVars }
    } catch (error) {
      console.error("Error parsing run parameters:", error)
      return { independentVars: {} }
    }
  }

  const getAllParameters = () => {
    const allParams: Record<string, Set<string | number>> = {}
    
    runs.forEach(run => {
      const { independentVars } = parseRunParameters(run)
      
      Object.entries(independentVars).forEach(([key, value]) => {
        if (!allParams[key]) {
          allParams[key] = new Set()
        }
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        allParams[key].add(value as any)
      })
    })
    
    return allParams
  }

  const allParams = getAllParameters()
  const paramKeys = Object.keys(allParams)
  
  if (paramKeys.length === 0) {
    return <p className="text-muted-foreground">No parameters defined for these runs</p>
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Run Parameters</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Parameter</TableHead>
              {runs.map((run, index) => (
                <TableHead key={run.run_id}>Run {index + 1}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {paramKeys.map(paramKey => (
              <TableRow key={paramKey}>
                <TableCell className="font-medium">{paramKey}</TableCell>
                {runs.map(run => {
                  const { independentVars } = parseRunParameters(run)
                  const value = independentVars[paramKey]
                  return (
                    <TableCell key={`${run.run_id}-${paramKey}`}>
                      {value !== undefined ? String(value) : '-'}
                    </TableCell>
                  )
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
} 