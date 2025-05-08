"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import * as z from "zod"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { createExperiment, updateExperiment, getProject, Project } from "@/lib/data"

const experimentSchema = z.object({
  name: z
    .string()
    .min(2, {
      message: "Experiment name must be at least 2 characters.",
    })
    .max(50, {
      message: "Experiment name must not exceed 50 characters.",
    }),
  description: z
    .string()
    .max(500, {
      message: "Description must not exceed 500 characters.",
    })
    .optional(),
  parameters: z.record(z.string(), z.string()).optional(),
})

interface ExperimentFormProps {
  projectId: string
  experiment?: {
    id: string
    name: string
    description?: string
    parameters?: string
  }
}

export function ExperimentForm({ projectId, experiment }: ExperimentFormProps) {
  const router = useRouter()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [project, setProject] = useState<Project | null>(null)
  const [independentVariables, setIndependentVariables] = useState<Record<string, string>>({})

  // Load project data to get independent variables
  useEffect(() => {
    const loadProject = async () => {
      try {
        const projectData = await getProject(projectId)
        setProject(projectData)
        
        // Initialize independent variables from experiment if it exists
        if (experiment?.parameters) {
          try {
            const params = typeof experiment.parameters === 'string' 
              ? JSON.parse(experiment.parameters) 
              : experiment.parameters;
            setIndependentVariables(params)
          } catch (e) {
            console.error("Error parsing experiment parameters:", e)
          }
        }
      } catch (error) {
        console.error("Error loading project:", error)
      }
    }
    
    loadProject()
  }, [projectId, experiment])

  const form = useForm<z.infer<typeof experimentSchema>>({
    resolver: zodResolver(experimentSchema),
    defaultValues: {
      name: experiment?.name || "",
      description: experiment?.description || "",
      parameters: experiment?.parameters 
        ? (typeof experiment.parameters === 'string' 
            ? JSON.parse(experiment.parameters) 
            : experiment.parameters) 
        : {},
    },
  })

  async function onSubmit(values: z.infer<typeof experimentSchema>) {
    setIsSubmitting(true)

    try {
      if (experiment) {
        // Update existing experiment
        await updateExperiment(projectId, experiment.id, {
          name: values.name,
          description: values.description || "",
          parameters: JSON.stringify(independentVariables)
        })
        router.push(`/projects/${projectId}/experiments/${experiment.id}`)
      } else {
        // Create new experiment
        const newExperiment = await createExperiment(projectId, values.name, values.description || "", independentVariables)
        router.push(`/projects/${projectId}/experiments/${newExperiment.experiment_id}`)
      }
    } catch (error) {
      console.error("Error saving experiment:", error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleIndependentVariableChange = (name: string, value: string) => {
    setIndependentVariables(prev => ({
      ...prev,
      [name]: value
    }))
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Experiment Name</FormLabel>
              <FormControl>
                <Input placeholder="Enter experiment name" {...field} />
              </FormControl>
              <FormDescription>A clear, descriptive name for your experiment.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Describe your experiment (optional)"
                  className="resize-none"
                  rows={3}
                  {...field}
                />
              </FormControl>
              <FormDescription>A brief description of what this experiment is testing.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <div>
          <h3 className="text-lg font-medium mb-4">Independent Variables</h3>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Independent Variable</TableHead>
                  <TableHead>Value</TableHead>
                  <TableHead>Units</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {project?.project_params?.independent && 
                 Array.isArray(project.project_params.independent) && 
                 project.project_params.independent.map((variable: { name: string; units?: string }) => (
                  <TableRow key={variable.name}>
                    <TableCell className="font-medium">{variable.name}</TableCell>
                    <TableCell>
                      <Input 
                        type="number" 
                        value={independentVariables[variable.name] || ""} 
                        onChange={(e) => handleIndependentVariableChange(variable.name, e.target.value)}
                        placeholder="Enter value"
                      />
                    </TableCell>
                    <TableCell>{variable.units || "-"}</TableCell>
                  </TableRow>
                ))}
                {(!project?.project_params?.independent || 
                  !Array.isArray(project.project_params.independent) || 
                  project.project_params.independent.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={3} className="text-center py-4 text-muted-foreground">
                      No independent variables defined for this project
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </div>

        <div className="flex justify-end gap-4">
          <Button type="button" variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : experiment ? "Update Experiment" : "Create Experiment"}
          </Button>
        </div>
      </form>
    </Form>
  )
}
