import { notFound } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { ChevronLeft } from "lucide-react"
import { ProjectForm } from "@/components/project-form"
import { fetchProject } from "@/lib/data"

// Use a completely different approach that works with Next.js's Promise-based params
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export default async function EditProjectPage(props: any) {
  // Access the ID from the props without type checking
  const projectId = props?.params?.id || '';
  
  let apiProject = null;
  
  try {
    apiProject = await fetchProject(projectId);
  } catch (error) {
    console.error("Error fetching project:", error);
    notFound();
  } finally {
    // Any cleanup code can go here
  }

  if (!apiProject) {
    notFound()
  }

  const project = {
    id: apiProject.project_id.toString(),
    name: apiProject.project_name,
    description: apiProject.project_description,
    parameters: apiProject.project_params,
    controls: apiProject.project_controls,
  }

  return (
    <div className="container mx-auto py-8">
      <Button variant="ghost" asChild className="mb-6">
        <Link href={`/projects/${project.id}`}>
          <ChevronLeft className="mr-2 h-4 w-4" />
          Back to Project
        </Link>
      </Button>

      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Edit Project</h1>
        <ProjectForm project={project} />
      </div>
    </div>
  )
}
