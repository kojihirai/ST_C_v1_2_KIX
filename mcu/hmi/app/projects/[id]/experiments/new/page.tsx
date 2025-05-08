import { notFound } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { ChevronLeft } from "lucide-react"
import { ExperimentForm } from "@/components/experiment-form"
import { fetchProject } from "@/lib/data"

// Use a completely different approach that works with Next.js's Promise-based params
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export default async function NewExperimentPage(props: any) {
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

  return (
    <div className="container mx-auto py-8">
      <Button variant="ghost" asChild className="mb-6">
        <Link href={`/projects/${apiProject.project_id}`}>
          <ChevronLeft className="mr-2 h-4 w-4" />
          Back to Project
        </Link>
      </Button>

      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">New Experiment</h1>
        
        <div className="rounded-lg border p-4 mb-8">
          <h2 className="text-lg font-medium">Project: {apiProject.project_name}</h2>
        </div>

        <ExperimentForm 
          projectId={String(apiProject.project_id)} 
        />
      </div>
    </div>
  )
}
