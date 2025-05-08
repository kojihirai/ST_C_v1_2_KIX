"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { MoreHorizontal, Trash } from "lucide-react"
import { fetchRuns, Run } from "@/lib/data"
import { formatDate } from "@/lib/utils"
import { DeleteConfirmDialog } from "@/components/delete-confirm-dialog"
import { RunParametersTable } from "@/components/run-parameters-table"

interface RunListProps {
  projectId: string
  experimentId: string
  hideParametersTable?: boolean
}

export function RunList({ projectId, experimentId, hideParametersTable = false }: RunListProps) {
  const [runs, setRuns] = useState<Run[]>([])
  const [runToDelete, setRunToDelete] = useState<Run | null>(null)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const loadRuns = async () => {
      try {
        setIsLoading(true)
        const data = await fetchRuns(projectId, experimentId)
        setRuns(data)
      } catch (error) {
        console.error("Error loading runs:", error)
      } finally {
        setIsLoading(false)
      }
    }

    loadRuns()
  }, [projectId, experimentId])

  const handleDeleteClick = (run: Run) => {
    setRunToDelete(run)
    setIsDeleteDialogOpen(true)
  }

  const handleConfirmDelete = async () => {
    if (runToDelete) {
      try {
        // This endpoint doesn't exist in the API yet
        // await deleteRun(projectId, experimentId, runToDelete.run_id)
        setRuns(runs.filter((r) => r.run_id !== runToDelete.run_id))
        setIsDeleteDialogOpen(false)
        setRunToDelete(null)
      } catch (error) {
        console.error("Error deleting run:", error)
      }
    }
  }

  if (isLoading) {
    return (
      <div className="text-center py-12">
        <p>Loading runs...</p>
      </div>
    )
  }

  if (runs.length === 0) {
    return (
      <div className="text-center py-12 border rounded-lg bg-muted/20">
        <h3 className="text-lg font-medium mb-2">No runs available</h3>
        <p className="text-muted-foreground">
          Create a new run to get started.
        </p>
      </div>
    )
  }

  return (
    <>
      {/* Parameters Summary Table - Only show if not hidden */}
      {!hideParametersTable && <RunParametersTable runs={runs} />}

      {/* Runs Table */}
      <div className="mb-6">
        <h2 className="text-2xl font-semibold">Runs ({runs.length})</h2>
      </div>
      
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Run Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="w-[80px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.map((run) => (
              <TableRow key={run.run_id}>
                <TableCell className="font-medium">
                  <Link href={`/projects/${projectId}/experiments/${experimentId}/runs/${run.run_id}`} className="hover:underline">
                    {run.run_name}
                  </Link>
                </TableCell>
                <TableCell>
                  <Badge variant={run.run_status === "completed" ? "default" : "outline"}>
                    {run.run_status}
                  </Badge>
                </TableCell>
                <TableCell>{formatDate(run.run_created_at)}</TableCell>
                <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreHorizontal className="h-4 w-4" />
                        <span className="sr-only">Actions</span>
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        className="text-destructive focus:text-destructive"
                        onClick={() => handleDeleteClick(run)}
                      >
                        <Trash className="mr-2 h-4 w-4" />
                        Delete run
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
        title="Delete Run"
        description="Are you sure you want to delete this run? This action cannot be undone."
      />
    </>
  )
}
