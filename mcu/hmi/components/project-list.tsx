"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { MoreHorizontal, Trash, Copy } from "lucide-react"
import { fetchProjects, duplicateProject, deleteProject, Project } from "@/lib/data"
import { formatDate } from "@/lib/utils"
import { DeleteConfirmDialog } from "@/components/delete-confirm-dialog"
import { useRouter } from "next/navigation"

export function ProjectList() {
  const router = useRouter()
  const [projects, setProjects] = useState<Project[]>([])
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isDuplicating, setIsDuplicating] = useState(false)

  useEffect(() => {
    const loadProjects = async () => {
      try {
        setIsLoading(true)
        const data = await fetchProjects()
        console.log("Projects data:", data)
        // Ensure each project has a valid project_id
        const validProjects = data.filter(project => project && project.project_id !== null && project.project_id !== undefined)
        console.log("Valid projects:", validProjects)
        setProjects(validProjects)
      } catch (error) {
        console.error("Error loading projects:", error)
      } finally {
        setIsLoading(false)
      }
    }

    loadProjects()
  }, [])

  const handleDeleteClick = (project: Project) => {
    setProjectToDelete(project)
    setIsDeleteDialogOpen(true)
  }

  const handleConfirmDelete = async () => {
    if (projectToDelete) {
      try {
        await deleteProject(projectToDelete.project_id)
        setProjects(projects.filter((p) => p.project_id !== projectToDelete.project_id))
        setIsDeleteDialogOpen(false)
        setProjectToDelete(null)
      } catch (error) {
        console.error("Error deleting project:", error)
      }
    }
  }

  const handleDuplicateClick = async (project: Project) => {
    try {
      setIsDuplicating(true)
      await duplicateProject(project.project_id.toString())
      
      // Refresh the projects list instead of manually adding the duplicated project
      const updatedProjects = await fetchProjects()
      setProjects(updatedProjects)
      
      // Refresh the page to ensure everything is in sync
      router.refresh()
    } catch (error) {
      console.error("Error duplicating project:", error)
    } finally {
      setIsDuplicating(false)
    }
  }

  if (isLoading) {
    return (
      <div className="text-center py-12">
        <p>Loading projects...</p>
      </div>
    )
  }

  if (projects.length === 0) {
    return (
      <div className="text-center py-12 border rounded-lg bg-muted/20">
        <h3 className="text-lg font-medium mb-2">No projects available</h3>
        <p className="text-muted-foreground">
          Create a new project to get started.
        </p>
      </div>
    )
  }

  return (
    <>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Project Name</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Experiments</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="w-[80px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {projects.map((project) => (
              <TableRow key={project.project_id}>
                <TableCell className="font-medium">
                  <Link href={`/projects/${project.project_id}`} className="hover:underline">
                    {project.project_name || "Unnamed Project"}
                  </Link>
                </TableCell>
                <TableCell>{project.project_description || "-"}</TableCell>
                <TableCell>
                  <Badge variant="outline">{project.experiment_count || 0}</Badge>
                </TableCell>
                <TableCell>{formatDate(project.project_created_at)}</TableCell>
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
                        onClick={() => handleDuplicateClick(project)}
                        disabled={isDuplicating}
                      >
                        <Copy className="mr-2 h-4 w-4" />
                        Duplicate project
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className="text-destructive focus:text-destructive"
                        onClick={() => handleDeleteClick(project)}
                      >
                        <Trash className="mr-2 h-4 w-4" />
                        Delete project
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
        title="Delete Project"
        description="Are you sure you want to delete this project? This action cannot be undone and will also delete all associated experiments and runs."
      />
    </>
  )
}
