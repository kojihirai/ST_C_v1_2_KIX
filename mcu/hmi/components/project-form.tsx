"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm, useFieldArray } from "react-hook-form"
import * as z from "zod"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { createProject, updateProject } from "@/lib/data"
import { Plus, Trash } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

type DrillDirection = "cw" | "ccw"
type LinearDirection = "fw" | "bw"

// Define the parameter schema
const parameterSchema = z.object({
  name: z.string().min(1, { message: "Name is required" }),
  value: z.union([z.string(), z.number()]).optional(),
  description: z.string().optional(),
  units: z.string().optional(),
})

// Define the project schema
const projectSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
  parameters: z.object({
    constants: z.array(parameterSchema).optional(),
    independent: z.array(parameterSchema).optional(),
    dependent: z.array(parameterSchema).optional(),
    general: z.array(parameterSchema).optional(),
  }).optional(),
  controls: z.object({
    drill: z.object({
      setpoint: z.number(),
      direction: z.enum(["cw", "ccw"]),
    }).optional(),
    linearActuator: z.object({
      setpoint: z.number(),
      direction: z.enum(["fw", "bw"]),
    }).optional(),
  }).optional(),
})

type ProjectFormValues = z.infer<typeof projectSchema>

interface ProjectFormProps {
  project?: {
    id: string
    name: string
    description?: string
    parameters?: {
      constants?: { name: string; value: string | number; description?: string; units?: string }[]
      independent?: { name: string; value: string | number; description?: string; units?: string }[]
      dependent?: { name: string; value: string | number; description?: string; units?: string }[]
      general?: { name: string; value: string | number; description?: string; units?: string }[]
    }
    controls?: {
      drill?: { setpoint: number; direction: DrillDirection }
      linearActuator?: { setpoint: number; direction: LinearDirection }
    }
  }
}

// Parameter input component
function ParameterInput({ 
  control, 
  name, 
  label, 
  description,
  isDependent = false,
  isIndependent = false
}: { 
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  control: any, 
  name: string, 
  label: string, 
  description: string,
  isDependent?: boolean,
  isIndependent?: boolean
}) {
  const { fields, append, remove } = useFieldArray({
    control,
    name,
  })

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-sm font-medium">{label}</h3>
        <Button 
          type="button" 
          variant="outline" 
          size="sm" 
          onClick={() => append({ name: "", value: "", description: "", units: "" })}
        >
          <Plus className="h-4 w-4 mr-1" /> Add Parameter
        </Button>
      </div>
      <p className="text-sm text-muted-foreground">{description}</p>
      
      {fields.length === 0 ? (
        <div className="text-center py-6 border rounded-md bg-muted/20">
          <p className="text-sm text-muted-foreground">No parameters added yet</p>
        </div>
      ) : (
        <div className="space-y-4">
          {fields.map((field, index) => (
            <Card key={field.id}>
              <CardContent className="pt-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <FormField
                    control={control}
                    name={`${name}.${index}.name`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Name</FormLabel>
                        <FormControl>
                          <Input placeholder="Parameter name" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  {!isDependent && !isIndependent && (
                    <FormField
                      control={control}
                      name={`${name}.${index}.value`}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Value</FormLabel>
                          <FormControl>
                            <Input placeholder="Parameter value" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  )}
                  
                  <FormField
                    control={control}
                    name={`${name}.${index}.description`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Description</FormLabel>
                        <FormControl>
                          <Input placeholder="Parameter description (optional)" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <FormField
                    control={control}
                    name={`${name}.${index}.units`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Units</FormLabel>
                        <FormControl>
                          <Input placeholder="Units (optional)" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                
                <div className="flex justify-end mt-4">
                  <Button 
                    type="button" 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => remove(index)}
                    className="text-destructive"
                  >
                    <Trash className="h-4 w-4 mr-1" /> Remove
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

export function ProjectForm({ project: initialProject }: ProjectFormProps = {}) {
  const router = useRouter()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const isEditing = !!initialProject?.id

  const form = useForm<ProjectFormValues>({
    resolver: zodResolver(projectSchema),
    defaultValues: {
      name: initialProject?.name || "",
      description: initialProject?.description || "",
      parameters: {
        constants: initialProject?.parameters?.constants || [],
        independent: initialProject?.parameters?.independent || [],
        dependent: initialProject?.parameters?.dependent || [],
        general: initialProject?.parameters?.general || [],
      },
      controls: {
        drill: {
          setpoint: initialProject?.controls?.drill?.setpoint || 0,
          direction: (initialProject?.controls?.drill?.direction as DrillDirection) || "cw",
        },
        linearActuator: {
          setpoint: initialProject?.controls?.linearActuator?.setpoint || 0,
          direction: (initialProject?.controls?.linearActuator?.direction as LinearDirection) || "fw",
        },
      },
    },
  })

  async function onSubmit(values: ProjectFormValues) {
    try {
      setIsSubmitting(true)
      
      const projectData = {
        project_name: values.name,
        project_description: values.description || "",
        project_params: values.parameters || {},
        project_controls: {
          drill: values.controls?.drill || { direction: "cw" },
          linearActuator: values.controls?.linearActuator || { direction: "fw" }
        }
      }
      
      if (isEditing && initialProject?.id) {
        // Update existing project
        await updateProject(parseInt(initialProject.id), projectData)
      } else {
        // Create new project
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        await createProject(projectData as any)
      }
      
      router.push("/projects")
      router.refresh()
    } catch (error) {
      console.error(isEditing ? "Error updating project:" : "Error creating project:", error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Project Name</FormLabel>
              <FormControl>
                <Input placeholder="Enter project name" {...field} />
              </FormControl>
              <FormDescription>
                This is the name of your project. It will be displayed in the project list.
              </FormDescription>
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
                  placeholder="Enter project description"
                  className="resize-none"
                  {...field}
                />
              </FormControl>
              <FormDescription>
                Provide a brief description of your project.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <div>
          <h3 className="text-lg font-medium mb-4">Parameters</h3>
          <Tabs defaultValue="general" className="w-full">
            <TabsList className="grid w-full grid-cols-4 mb-4">
              <TabsTrigger value="general">General</TabsTrigger>
              <TabsTrigger value="constants">Constants</TabsTrigger>
              <TabsTrigger value="independent">Independent Variables</TabsTrigger>
              <TabsTrigger value="dependent">Dependent Variables</TabsTrigger>
            </TabsList>

            <TabsContent value="general">
              <ParameterInput 
                control={form.control}
                name="parameters.general"
                label="General Parameters"
                description="Enter general project parameters. These are overall project settings and metadata."
              />
            </TabsContent>

            <TabsContent value="constants">
              <ParameterInput 
                control={form.control}
                name="parameters.constants"
                label="Constant Parameters"
                description="Enter constant parameters. These are values that remain fixed throughout the project."
              />
            </TabsContent>

            <TabsContent value="independent">
              <ParameterInput 
                control={form.control}
                name="parameters.independent"
                label="Independent Variables"
                description="Enter independent variables. These are variables that you manipulate in your experiments. Specific values will be set at the experiment level."
                isIndependent={true}
              />
            </TabsContent>

            <TabsContent value="dependent">
              <ParameterInput 
                control={form.control}
                name="parameters.dependent"
                label="Dependent Variables"
                description="Enter dependent variables. These are variables that are measured as outcomes of your experiments."
                isDependent={true}
              />
            </TabsContent>
          </Tabs>
        </div>

        <div>
          <h3 className="text-lg font-medium mb-4">Controls</h3>
          <Tabs defaultValue="drill" className="w-full">
            <TabsList className="grid w-full grid-cols-2 mb-4">
              <TabsTrigger value="drill">Drill</TabsTrigger>
              <TabsTrigger value="linear">Linear Actuator</TabsTrigger>
            </TabsList>

            <TabsContent value="drill">
              <div className="space-y-4">
                <FormField
                  control={form.control}
                  name="controls.drill.setpoint"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Setpoint (V)</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={0}
                          max={24}
                          step={0.1}
                          {...field}
                          onChange={(e) => field.onChange(Number(e.target.value))}
                        />
                      </FormControl>
                      <FormDescription>Set the drill effective voltage (0-24V).</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="controls.drill.direction"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Direction</FormLabel>
                      <Select 
                        onValueChange={field.onChange} 
                        defaultValue={field.value}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select direction" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="cw">Clockwise (CW)</SelectItem>
                          <SelectItem value="ccw">Counter-clockwise (CCW)</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormDescription>Select the drill rotation direction.</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </TabsContent>

            <TabsContent value="linear">
              <div className="space-y-4">
                <FormField
                  control={form.control}
                  name="controls.linearActuator.setpoint"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Setpoint (mm/s)</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={0}
                          max={15}
                          step={0.01}
                          {...field}
                          onChange={(e) => field.onChange(Number(e.target.value))}
                        />
                      </FormControl>
                      <FormDescription>Set the linear actuator speed in millimeters per second (0-15 mm/s).</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="controls.linearActuator.direction"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Direction</FormLabel>
                      <Select 
                        onValueChange={field.onChange} 
                        defaultValue={field.value}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select direction" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="fw">Forward (FW)</SelectItem>
                          <SelectItem value="bw">Backward (BW)</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormDescription>Select the linear actuator movement direction.</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </TabsContent>
          </Tabs>
        </div>

        <div className="flex justify-end gap-4">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting 
              ? (isEditing ? "Updating..." : "Creating...") 
              : (isEditing ? "Update Project" : "Create Project")}
          </Button>
        </div>
      </form>
    </Form>
  )
}
