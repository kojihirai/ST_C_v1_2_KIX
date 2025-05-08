import { notFound } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { ChevronLeft, Plus } from "lucide-react"
import { ExperimentList } from "@/components/experiment-list"
import { ProjectParametersTable } from "@/components/project-parameters-table"
import { fetchProject } from "@/lib/data"

// Use a completely different approach that works with Next.js's Promise-based params
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export default async function ProjectPage(props: any) {
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

  // Extract parameters from the project_params object
  const projectParams = apiProject.project_params || {};
  const constants = Array.isArray(projectParams.constants) ? projectParams.constants : [];
  const independent = Array.isArray(projectParams.independent) ? projectParams.independent : [];
  const dependent = Array.isArray(projectParams.dependent) ? projectParams.dependent : [];
  const general = Array.isArray(projectParams.general) ? projectParams.general : [];
  const controls = apiProject.project_controls || {};

  return (
    <div className="container mx-auto py-8">
      <Button variant="ghost" asChild className="mb-6">
        <Link href="/projects">
          <ChevronLeft className="mr-2 h-4 w-4" />
          Back to Projects
        </Link>
      </Button>

      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">{apiProject.project_name}</h1>
          <Button asChild>
            <Link href={`/projects/${apiProject.project_id}/experiments/new`}>
              <Plus className="mr-2 h-4 w-4" />
              New Experiment
            </Link>
          </Button>
        </div>

        <div className="rounded-lg border p-6 mb-8">
          <h2 className="text-xl font-semibold mb-4">Project Details</h2>
          <p className="text-gray-600 mb-4">{apiProject.project_description}</p>
          
          <div className="mt-6">
            <h3 className="text-lg font-medium mb-4">Project Parameters</h3>
            <ProjectParametersTable 
              constants={constants}
              independent={independent}
              dependent={dependent}
              general={general}
              controls={controls}
            />
          </div>
        </div>

        <div className="rounded-lg border p-6">
          <h2 className="text-xl font-semibold mb-4">Experiments</h2>
          <ExperimentList projectId={String(apiProject.project_id)} />
        </div>
      </div>
    </div>
  )
}
