import axios from 'axios';

// API base URL - adjust as needed
// const API_BASE_URL = 'http://localhost:8000';
const API_BASE_URL = 'http://10.147.18.184:8000';
// Type definitions for parameters
export interface ProjectParams {
  [key: string]: string | number | boolean | null | ProjectParams;
}

export interface ProjectControls {
  [key: string]: string | number | boolean | null | ProjectControls;
}

export interface ExperimentParams {
  [key: string]: string | number | boolean | null | ExperimentParams;
}

export interface RunParams {
  [key: string]: string | number | boolean | null | RunParams;
}

// Create axios instance with default config
const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  withCredentials: true, // This is important for CORS with credentials
});

// Add request interceptor to handle CORS preflight
axiosInstance.interceptors.request.use(
  (config) => {
    // For OPTIONS requests, ensure proper headers are set
    if (config.method?.toLowerCase() === 'options') {
      if (config.headers) {
        config.headers['Access-Control-Request-Method'] = 'GET,POST,PUT,DELETE,OPTIONS';
        config.headers['Access-Control-Request-Headers'] = 'Content-Type,Accept';
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle CORS errors
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 405 && error.config?.method?.toLowerCase() === 'options') {
      // For OPTIONS requests, return an empty success response
      return Promise.resolve({ data: {} });
    }
    return Promise.reject(error);
  }
);

// Types
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
  run_params?: RunParams;
  run_status: string;
  run_created_at: string;
  run_modified_at: string;
  start_time?: string;
  stop_time?: string;
}

export interface RunVideo {
  video_id: number;
  run_id: number;
  video_path: string;
  video_created_at: string;
}

export interface CommandResponse {
  success: boolean;
  message?: string;
  data?: unknown;
}

export interface Command {
  [key: string]: string | number | boolean | null | Record<string, unknown>;
}

// Project API
export const createProject = async (data: {
  project_name: string;
  project_description?: string;
  project_params?: ProjectParams;
  project_controls?: ProjectControls;
}): Promise<Project> => {
  const response = await axiosInstance.post('/projects', data);
  return response.data;
};

export const deleteProject = async (projectId: number): Promise<void> => {
  await axiosInstance.delete(`/projects/${projectId}`);
};

export const getProjects = async (): Promise<Project[]> => {
  try {
    const response = await axiosInstance.get('/projects');
    
    // Check if response.data is an array of arrays
    if (Array.isArray(response.data) && response.data.length > 0 && Array.isArray(response.data[0])) {
      // Convert array of arrays to array of project objects
      return response.data.map((row: unknown[]) => {
        // Assuming the order of fields in the array matches the Project interface
        return {
          project_id: row[0] as number,
          project_name: row[1] as string,
          project_description: row[2] as string | undefined,
          project_params: row[3] as ProjectParams | undefined,
          project_controls: row[4] as ProjectControls | undefined,
          experiment_count: parseInt(row[5] as string) || 0,
          project_created_at: row[6] as string,
          project_modified_at: row[7] as string
        };
      });
    }
    
    // If it's already an array of objects, return it
    if (Array.isArray(response.data)) {
      return response.data.map(project => ({
        ...project,
        experiment_count: parseInt(project.experiment_count) || 0
      }));
    }
    
    console.error("Unexpected response format:", typeof response.data);
    return [];
  } catch (error) {
    console.error("Error fetching projects:", error);
    return [];
  }
};

export const getProject = async (projectId: number): Promise<Project> => {
  const response = await axiosInstance.get(`/projects/${projectId}`);
  return response.data;
};

export const updateProject = async (projectId: number, data: {
  project_name: string;
  project_description?: string;
  project_params?: ProjectParams;
  project_controls?: ProjectControls;
}): Promise<Project> => {
  const response = await axiosInstance.put(`/projects/${projectId}`, data);
  return response.data;
};

// Experiment API
export const createExperiment = async (data: {
  project_id: number;
  experiment_name: string;
  experiment_description?: string;
  experiment_params?: ExperimentParams;
}): Promise<Experiment> => {
  const response = await axiosInstance.post('/experiments', data);
  return response.data;
};

export const getExperimentsByProject = async (projectId: number): Promise<Experiment[]> => {
  try {
    const response = await axiosInstance.get(`/projects/${projectId}/experiments`);
    console.log("Raw API response for experiments:", response.data);
    
    // Check if response.data is an array of arrays
    if (Array.isArray(response.data) && response.data.length > 0 && Array.isArray(response.data[0])) {
      console.log("Converting array of arrays to objects");
      // Convert array of arrays to array of experiment objects
      return response.data.map((row: unknown[]) => {
        const experiment = {
          experiment_id: row[0] as number,
          project_id: row[1] as number,
          experiment_name: row[2] as string,
          experiment_description: row[3] as string | undefined,
          experiment_params: row[4] as ExperimentParams | undefined,
          run_count: row[5] as number || 0,
          created_at: row[6] as string,
          modified_at: row[7] as string
        };
        console.log("Converted experiment:", experiment);
        return experiment;
      });
    }
    
    // If it's already an array of objects, return it
    if (Array.isArray(response.data)) {
      console.log("Response is already array of objects");
      return response.data;
    }
    
    console.error("Unexpected response format:", typeof response.data);
    return [];
  } catch (error) {
    console.error("Error fetching experiments:", error);
    return [];
  }
};

export const getExperiment = async (projectId: number, experimentId: number): Promise<Experiment> => {
  try {
    const response = await axiosInstance.get(`/projects/${projectId}/experiments/${experimentId}`);
    
    // Check if response.data is an array
    if (Array.isArray(response.data)) {
      // Convert array to experiment object
      return {
        experiment_id: response.data[0],
        project_id: response.data[1],
        experiment_name: response.data[2],
        experiment_description: response.data[3],
        experiment_params: response.data[4],
        run_count: response.data[5] || 0,
        created_at: response.data[6],
        modified_at: response.data[7]
      };
    }
    
    // If it's already an object, return it
    return response.data;
  } catch (error) {
    console.error("Error fetching experiment:", error);
    throw error;
  }
};

export const updateExperiment = async (projectId: number, experimentId: number, data: {
  experiment_name: string;
  experiment_description?: string;
  experiment_params?: ExperimentParams;
}): Promise<Experiment> => {
  const response = await axiosInstance.put(`/projects/${projectId}/experiments/${experimentId}`, data);
  return response.data;
};

// Run API
export const createRun = async (projectId: number, experimentId: number, data: {
  run_name: string;
  run_description?: string;
  run_params?: RunParams;
  run_status: string;
  start_time?: string;
  stop_time?: string;
}): Promise<Run> => {
  const response = await axiosInstance.post(
    `/projects/${projectId}/experiments/${experimentId}/runs`,
    data
  );
  return response.data;
};

export const getRunsByExperiment = async (projectId: number, experimentId: number): Promise<Run[]> => {
  try {
    const response = await axiosInstance.get(`/projects/${projectId}/experiments/${experimentId}/runs`);
    
    // Check if response.data is an array of arrays
    if (Array.isArray(response.data) && response.data.length > 0 && Array.isArray(response.data[0])) {
      // Convert array of arrays to array of run objects
      return response.data.map((row: unknown[]) => {
        // Assuming the order of fields in the array matches the Run interface
        return {
          run_id: row[0] as number,
          project_id: row[1] as number,
          experiment_id: row[2] as number,
          run_name: row[3] as string,
          run_description: row[4] as string | undefined,
          run_params: row[5] as RunParams | undefined,
          run_status: row[6] as string,
          run_created_at: row[7] as string,
          run_modified_at: row[8] as string,
          start_time: row[9] as string | undefined,
          stop_time: row[10] as string | undefined
        };
      });
    }
    
    // If it's already an array of objects, return it
    if (Array.isArray(response.data)) {
      return response.data;
    }
    
    console.error("Unexpected response format:", typeof response.data);
    return [];
  } catch (error) {
    console.error("Error fetching runs:", error);
    return [];
  }
};

export const stopRun = async (runId: number, data: {
  status: string;
  notes?: string;
}): Promise<void> => {
  await axiosInstance.post(`/runs/${runId}/stop`, data);
};

// Run Video API
export const createRunVideo = async (data: {
  run_id: number;
  video_path: string;
}): Promise<RunVideo> => {
  const response = await axiosInstance.post('/run_videos', data);
  return response.data;
};

export const getVideosByRun = async (runId: number): Promise<RunVideo[]> => {
  const response = await axiosInstance.get(`/runs/${runId}/videos`);
  return response.data;
};

// Control System API
export const sendCommand = async (data: {
  device: "lcu" | "dcu",
  command: {
    mode: number,
    direction: number,
    target: number,
    pid_setpoint?: number,
    duration?: number,
    project_id?: number,
    experiment_id?: number,
    run_id?: number
  }
}): Promise<CommandResponse> => {
  try {
    // Ensure command is properly nested
    const commandPayload = {
      device: data.device,
      command: {
        mode: data.command.mode,
        direction: data.command.direction,
        target: data.command.target,
        pid_setpoint: data.command.pid_setpoint ?? 0,
        duration: data.command.duration ?? 0,
        project_id: data.command.project_id ?? 0,
        experiment_id: data.command.experiment_id ?? 0,
        run_id: data.command.run_id ?? 0
      }
    }

    console.log(`Sending ${data.device} command:`, commandPayload)
    const response = await axiosInstance.post('/send_command/', commandPayload)
    console.log(`${data.device} command response:`, response.data)
    return response.data
  } catch (error) {
    console.error(`Error sending ${data.device} command:`, error)
    return { success: false, message: error instanceof Error ? error.message : 'Unknown error' }
  }
};

export const emergencyStop = async (): Promise<CommandResponse> => {
  const response = await axiosInstance.post('/emergency_stop');
  return response.data;
};

// Create a default export with all API functions
const apiClient = {
  createProject,
  getProjects,
  getProject,
  updateProject,
  createExperiment,
  getExperimentsByProject,
  getExperiment,
  updateExperiment,
  createRun,
  getRunsByExperiment,
  stopRun,
  createRunVideo,
  getVideosByRun,
  sendCommand,
  emergencyStop,
  fetchProjects: getProjects,
  fetchExperimentsByProject: getExperimentsByProject,
  fetchExperimentVariables: async (projectId: number, experimentId: number) => {
    const experiment = await getExperiment(projectId, experimentId);
    return experiment.experiment_params || {};
  },
  fetchExperimentControls: async (projectId: number) => {
    const project = await getProject(projectId);
    return project.project_controls || {};
  },
  endRun: stopRun,
};

export default apiClient;
