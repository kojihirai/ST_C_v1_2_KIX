import { notFound } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { ChevronLeft } from "lucide-react"
import { RunList } from "@/components/run-list"
import { fetchProject, fetchExperiment } from "@/lib/data"
import { formatDate } from "@/lib/utils"
import { ExperimentParametersTable } from "@/components/experiment-parameters-table"

// Use a completely different approach that works with Next.js's Promise-based params
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export default async function ExperimentPage(props: any) {
  // Access the IDs from the props without type checking
  const projectId = props?.params?.id || '';
  const experimentId = props?.params?.experimentId || '';
  
  let apiProject = null;
  let apiExperiment = null;
  
  try {
    apiProject = await fetchProject(projectId);
    apiExperiment = await fetchExperiment(projectId, experimentId);
  } catch (error) {
    console.error("Error fetching data:", error);
    notFound();
  } finally {
    // Any cleanup code can go here
  }

  if (!apiProject || !apiExperiment) {
    notFound()
  }

  // Parse experiment parameters
  let parsedParameters: Record<string, string | number | boolean> = {};
  if (apiExperiment.experiment_params) {
    try {
      const rawParams = typeof apiExperiment.experiment_params === 'string' 
        ? JSON.parse(apiExperiment.experiment_params) 
        : apiExperiment.experiment_params;
      
      // Filter out null values and ensure correct types
      parsedParameters = Object.fromEntries(
        Object.entries(rawParams)
          .filter(([, value]) => value !== null)
          .map(([key, value]) => [key, value as string | number | boolean])
      );
    } catch (e) {
      console.error("Error parsing experiment parameters:", e);
    }
  }

  // Get independent variables from project and ensure correct type
  const independentVariables = Array.isArray(apiProject.project_params?.independent) 
    ? apiProject.project_params.independent
    : [];

  return (
    <div className="container mx-auto py-8">
      <Button variant="ghost" asChild className="mb-6">
        <Link href={`/projects/${apiProject.project_id}`}>
          <ChevronLeft className="mr-2 h-4 w-4" />
          Back to Project
        </Link>
      </Button>

      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold">{apiExperiment.experiment_name}</h1>
            <p className="text-muted-foreground mt-2">{apiExperiment.experiment_description || 'No description'}</p>
            <p className="text-sm text-muted-foreground mt-1">
              Created: {formatDate(apiExperiment.created_at)}
            </p>
          </div>
          <Button asChild>
            <Link href={`/projects/${apiProject.project_id}/experiments/${apiExperiment.experiment_id}/edit`}>
              Edit Experiment
            </Link>
          </Button>
        </div>

        <div className="grid gap-8">
          <div>
            <h2 className="text-xl font-semibold mb-4">Parameters</h2>
            <ExperimentParametersTable 
              parameters={parsedParameters}
              independentVariables={independentVariables}
            />
          </div>

          <div>
            <h2 className="text-xl font-semibold mb-4">Runs</h2>
            <RunList 
              projectId={String(apiProject.project_id)} 
              experimentId={String(apiExperiment.experiment_id)} 
            />
          </div>
        </div>
      </div>
    </div>
  )
}
