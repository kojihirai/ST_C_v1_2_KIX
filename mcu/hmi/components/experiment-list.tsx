"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { MoreHorizontal, Trash } from "lucide-react"
import { fetchExperiments, Experiment, getProject } from "@/lib/data"
import { formatDate } from "@/lib/utils"
import { DeleteConfirmDialog } from "@/components/delete-confirm-dialog"
import React from "react"

interface ExperimentListProps {
  projectId: string
}

interface IndependentVariable {
  name: string;
  units?: string;
}

export function ExperimentList({ projectId }: ExperimentListProps) {
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [experimentToDelete, setExperimentToDelete] = useState<Experiment | null>(null)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [independentVariables, setIndependentVariables] = useState<IndependentVariable[]>([])

  useEffect(() => {
    const loadData = async () => {
      try {
        setIsLoading(true)
        // Load project data to get independent variables
        const projectData = await getProject(projectId)
        
        // Extract independent variable names and units from project parameters
        if (projectData?.project_params?.independent && Array.isArray(projectData.project_params.independent)) {
          const vars = projectData.project_params.independent.map((var_: { name: string; units?: string }) => ({
            name: var_.name,
            units: var_.units
          }))
          setIndependentVariables(vars)
        }
        
        // Load experiments
        const experimentsData = await fetchExperiments(projectId)
        setExperiments(experimentsData)
      } catch (error) {
        console.error("Error loading data:", error)
      } finally {
        setIsLoading(false)
      }
    }

    loadData()
  }, [projectId])

  const handleDeleteClick = (experiment: Experiment) => {
    setExperimentToDelete(experiment)
    setIsDeleteDialogOpen(true)
  }

  const handleConfirmDelete = async () => {
    if (experimentToDelete) {
      try {
        // This endpoint doesn't exist in the API yet
        // await deleteExperiment(projectId, experimentToDelete.experiment_id)
        setExperiments(experiments.filter((e) => e.experiment_id !== experimentToDelete.experiment_id))
        setIsDeleteDialogOpen(false)
        setExperimentToDelete(null)
      } catch (error) {
        console.error("Error deleting experiment:", error)
      }
    }
  }

  // Helper function to get experiment parameter value
  const getParameterValue = (experiment: Experiment, paramName: string) => {
    if (!experiment.experiment_params) return "-"
    
    // Handle both string and object formats
    if (typeof experiment.experiment_params === 'string') {
      try {
        const params = JSON.parse(experiment.experiment_params)
        return params[paramName] !== undefined ? params[paramName] : "-"
      } catch {
        return "-"
      }
    } else {
      return experiment.experiment_params[paramName] !== undefined 
        ? experiment.experiment_params[paramName] 
        : "-"
    }
  }

  if (isLoading) {
    return <div>Loading experiments...</div>
  }

  if (experiments.length === 0) {
    return (
      <div className="text-center py-8 border rounded-md">
        <p className="text-muted-foreground">No experiments found for this project.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Variable</TableHead>
              <TableHead>Runs</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Modified</TableHead>
              <TableHead className="w-[50px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {experiments.map((experiment) => (
              <TableRow key={experiment.experiment_id}>
                <TableCell className="font-medium">
                  <Link href={`/projects/${projectId}/experiments/${experiment.experiment_id}`}>
                    {experiment.experiment_name}
                  </Link>
                </TableCell>
                <TableCell>{experiment.experiment_description || "-"}</TableCell>
                <TableCell>
                  <div className="space-y-1">
                    {independentVariables.map((variable) => (
                      <div key={`${experiment.experiment_id}-${variable.name}`}>
                        {variable.name}: {getParameterValue(experiment, variable.name)}
                        {variable.units ? ` ${variable.units}` : ''}
                      </div>
                    ))}
                  </div>
                </TableCell>
                <TableCell>{experiment.run_count || 0}</TableCell>
                <TableCell>{formatDate(experiment.created_at)}</TableCell>
                <TableCell>{formatDate(experiment.modified_at)}</TableCell>
                <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" className="h-8 w-8 p-0">
                        <span className="sr-only">Open menu</span>
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        className="text-destructive"
                        onClick={() => handleDeleteClick(experiment)}
                      >
                        <Trash className="mr-2 h-4 w-4" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <DeleteConfirmDialog
        isOpen={isDeleteDialogOpen}
        onClose={() => setIsDeleteDialogOpen(false)}
        onConfirm={handleConfirmDelete}
        title="Delete Experiment"
        description="Are you sure you want to delete this experiment? This action cannot be undone."
      />
    </div>
  )
}
