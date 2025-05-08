// Data layer for projects and experiments
// Uses the API client to interact with the backend

import apiClient, {
  getProjects,
  getProject as apiGetProject,
  createProject as apiCreateProject,
  getExperimentsByProject,
  getExperiment,
  createExperiment as apiCreateExperiment,
  getRunsByExperiment,
  createRun as apiCreateRun,
  stopRun as apiStopRun,
  ProjectParams,
  ProjectControls,
  ExperimentParams
} from './api-client';

// Define types to match API client exactly
export interface Project {
  project_id: number;
  project_name: string;
  project_description?: string;
  project_params?: ProjectParams;
  project_controls?: ProjectControls;
  experiment_count: number;
  project_created_at: string;
  project_modified_at: string;
}

export interface Experiment {
  experiment_id: number;
  project_id: number;
  experiment_name: string;
  experiment_description?: string;
  experiment_params?: ExperimentParams;
  run_count: number;
  created_at: string;
  modified_at: string;
}

export interface Run {
  run_id: number;
  project_id: number;
  experiment_id: number;
  run_name: string;
  run_description?: string;
  run_params?: Record<string, unknown>;
  run_status: string;
  run_created_at: string;
  run_modified_at: string;
  start_time?: string;
  stop_time?: string;
}

// API functions
export async function fetchProjects(): Promise<Project[]> {
  try {
    const projects = await getProjects();
    return projects;
  } catch (error) {
    console.error("Error fetching projects:", error);
    return [];
  }
}

export async function getProject(id: string): Promise<Project | null> {
  try {
    return await apiGetProject(parseInt(id));
  } catch (error) {
    console.error(`Error fetching project ${id}:`, error);
    return null;
  }
}

// Alias for backward compatibility
export const fetchProject = getProject;

export async function createProject(data: {
  project_name: string;
  project_description?: string;
  project_params?: ProjectParams;
  project_controls?: ProjectControls;
}): Promise<Project> {
  try {
    return await apiCreateProject(data);
  } catch (error) {
    console.error("Error creating project:", error);
    throw error;
  }
}

export async function fetchExperiments(projectId: string): Promise<Experiment[]> {
  try {
    return await getExperimentsByProject(parseInt(projectId));
  } catch (error) {
    console.error(`Error fetching experiments for project ${projectId}:`, error);
    return [];
  }
}

export async function fetchExperiment(projectId: string, experimentId: string) {
  if (!projectId || !experimentId) {
    throw new Error('Project ID and Experiment ID are required');
  }
  try {
    const experiment = await getExperiment(parseInt(projectId), parseInt(experimentId));
    return experiment;
  } catch (error) {
    console.error('Error fetching experiment:', error);
    throw error;
  }
}

export async function createExperiment(
  projectId: string,
  name: string,
  description: string = "",
  parameters: ExperimentParams = {}
): Promise<Experiment> {
  try {
    return await apiCreateExperiment({
      project_id: parseInt(projectId),
      experiment_name: name,
      experiment_description: description,
      experiment_params: parameters
    });
  } catch (error) {
    console.error("Error creating experiment:", error);
    throw error;
  }
}

export async function deleteExperiment(id: string): Promise<void> {
  // Implementation
  console.log(`Deleting experiment with ID: ${id}`);
  // Return void explicitly
  return;
}

export async function updateExperiment(projectId: string, experimentId: string, data: { 
  name: string; 
  description?: string; 
  parameters?: string 
}): Promise<Experiment> {
  try {
    // Convert parameters string to Record<string, unknown> if provided
    const experimentParams = data.parameters ? JSON.parse(data.parameters) : undefined;
    
    // Call the API to update the experiment
    const updatedExperiment = await apiClient.updateExperiment(
      parseInt(projectId),
      parseInt(experimentId),
      {
        experiment_name: data.name,
        experiment_description: data.description,
        experiment_params: experimentParams
      }
    );
    
    return updatedExperiment;
  } catch (error) {
    console.error('Error updating experiment:', error);
    throw error;
  }
}

export async function fetchRuns(projectId: string, experimentId: string) {
  try {
    const runs = await getRunsByExperiment(parseInt(projectId), parseInt(experimentId));
    return runs;
  } catch (error) {
    console.error('Error fetching runs:', error);
    throw error;
  }
}

export async function deleteRun(): Promise<void> {
  // This endpoint doesn't exist in the API yet, so we'll throw an error
  throw new Error("Delete run endpoint not implemented in the API");
}

export async function createRun(projectId: string, experimentId: string, name: string): Promise<Run> {
  try {
    return await apiCreateRun({
      project_id: parseInt(projectId),
      experiment_id: parseInt(experimentId),
      run_name: name,
      run_status: "pending"
    });
  } catch (error) {
    console.error("Error creating run:", error);
    throw error;
  }
}

export async function stopRun(projectId: string, experimentId: string, runId: string, status: string = "completed", notes: string = ""): Promise<void> {
  try {
    await apiStopRun(parseInt(runId), { status, notes });
  } catch (error) {
    console.error(`Error stopping run ${runId}:`, error);
    throw error;
  }
}

export const updateProject = async (projectId: number, data: {
  project_name: string;
  project_description?: string;
  project_params?: Record<string, unknown>;
  project_controls?: Record<string, unknown>;
}): Promise<Project> => {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return await apiClient.updateProject(projectId, data as any);
  } catch (error) {
    console.error('Error updating project:', error);
    throw error;
  }
};

export async function duplicateProject(projectId: string): Promise<Project> {
  try {
    const originalProject = await getProject(projectId);
    if (!originalProject) {
      throw new Error(`Project ${projectId} not found`);
    }

    const newProjectData = {
      project_name: originalProject.project_name ? `${originalProject.project_name} (Copy)` : "Unnamed Project (Copy)",
      project_description: originalProject.project_description,
      project_params: originalProject.project_params as ProjectParams | undefined,
      project_controls: originalProject.project_controls as ProjectControls | undefined
    };

    const newProject = await createProject(newProjectData);

    // Duplicate experiments for the new project
    const experiments = await fetchExperiments(projectId);
    for (const experiment of experiments) {
      await createExperiment(
        newProject.project_id.toString(),
        experiment.experiment_name,
        experiment.experiment_description || "",
        experiment.experiment_params as ExperimentParams | undefined
      );
    }

    return newProject;
  } catch (error) {
    console.error("Error duplicating project:", error);
    throw error;
  }
}

// Create a default export with all data functions
const dataFunctions = {
  createProject,
  getProjects: fetchProjects,
  getProject,
  updateProject,
  deleteProject: deleteExperiment,
  duplicateProject,
  createExperiment,
  getExperiments: fetchExperiments,
  getExperiment: fetchExperiment,
  updateExperiment,
  deleteExperiment,
  createRun,
  getRuns: fetchRuns,
  getRun: getExperiment,
  updateRun: updateExperiment,
  deleteRun,
  startRun: createRun,
  endRun: stopRun
};

export default dataFunctions; 