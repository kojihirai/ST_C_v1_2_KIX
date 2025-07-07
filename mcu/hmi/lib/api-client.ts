import axios from 'axios';

// API base URL - adjust as needed
const API_BASE_URL = typeof window !== 'undefined' 
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : 'http://localhost:8000';
// const API_BASE_URL = 'http://10.147.18.184:8000';

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

export interface CommandResponse {
  success: boolean;
  message?: string;
  data?: unknown;
}

export const sendCommand = async (data: {
  device: "lcu" | "dcu",
  command: {
    mode: number,
    direction: number,
    target: number
  }
}): Promise<CommandResponse> => {
  try {
    const response = await axiosInstance.post('/send_command/', {
      device: data.device,
      command: data.command
    });
    return response.data;
  } catch (error) {
    console.error('Error sending command:', error);
    return {
      success: false,
      message: error instanceof Error ? error.message : 'Unknown error occurred'
    };
  }
};

// Default export
export default {
  sendCommand
};
