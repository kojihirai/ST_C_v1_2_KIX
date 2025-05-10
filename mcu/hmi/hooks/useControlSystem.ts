import { useState, useEffect } from "react"
import { websocket } from "@/lib/websocket"
import { SystemMode, SystemStatus, LcuDirection, DcuDirection, LcuCommand, DcuCommand } from "@/lib/constants"
import { getLcuParams, getDcuParams } from "@/lib/control-utils"
import apiClient, { Project, Experiment } from "@/lib/api-client"

// Define a type for the experiment metadata
interface ExperimentMetadataWithVariables extends Experiment {
  variables?: Record<string, any>;
  controls?: Record<string, any>;
}

export function useControlSystem() {
  const [mode, setMode] = useState<SystemMode>("manual")
  const [systemStatus, setSystemStatus] = useState<SystemStatus>("stopped")
  const [wsConnected, setWsConnected] = useState(false)
  
  // Project and Experiment state
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null)
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [selectedExperiment, setSelectedExperiment] = useState<number | null>(null)
  const [experimentMetadata, setExperimentMetadata] = useState<ExperimentMetadataWithVariables | null>(null)
  const [currentRunId, setCurrentRunId] = useState<number | null>(null)

  // Load projects on mount
  useEffect(() => {
    const loadProjects = async () => {
      console.log('Attempting to load projects...')
      try {
        const projectsData = await apiClient.fetchProjects()
        console.log('Received projects:', projectsData)
        setProjects(projectsData)
      } catch (error) {
        console.error('Error loading projects:', error)
      }
    }
    loadProjects()
  }, [])

  // Load experiments when a project is selected
  useEffect(() => {
    const loadExperiments = async () => {
      if (selectedProjectId) {
        console.log(`Loading experiments for project ${selectedProjectId}...`)
        try {
          const experimentsData = await apiClient.fetchExperimentsByProject(selectedProjectId)
          console.log('Received experiments:', experimentsData)
          setExperiments(experimentsData)
        } catch (error) {
          console.error('Error loading experiments:', error)
        }
      } else {
        setExperiments([])
      }
    }
    loadExperiments()
  }, [selectedProjectId])

  // Load experiment metadata when an experiment is selected
  useEffect(() => {
    const loadExperimentData = async () => {
      if (selectedProjectId && selectedExperiment) {
        console.log(`Loading data for project ${selectedProjectId}, experiment ${selectedExperiment}...`)
        try {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const experiment = await apiClient.getExperiment(selectedProjectId, selectedExperiment) as any
          
          console.log('Received experiment data:', experiment)
          
          // Parse experiment parameters if they're in string format
          let parsedParams = {};
          if (experiment.experiment_params) {
            try {
              parsedParams = typeof experiment.experiment_params === 'string' 
                ? JSON.parse(experiment.experiment_params)
                : experiment.experiment_params;
            } catch (e) {
              console.error('Error parsing experiment parameters:', e);
            }
          }
          
          // Set the experiment metadata with the parsed variables and controls
          setExperimentMetadata({
            ...experiment,
            variables: parsedParams,
            controls: experiment.controls || {}
          })
          
          console.log('Parsed experiment parameters:', parsedParams)
        } catch (error) {
          console.error('Error loading experiment data:', error)
        }
      } else {
        setExperimentMetadata(null)
      }
    }
    loadExperimentData()
  }, [selectedProjectId, selectedExperiment])

  const [manualStatus, setManualStatus] = useState<SystemStatus>("stopped")
  const [experimentStatus, setExperimentStatus] = useState<SystemStatus>("stopped")

  const [lcuMode, setLcuMode] = useState<string>("run_cont")
  const [dcuMode, setDcuMode] = useState<string>("run_cont")
  const [lcuDirection, setLcuDirection] = useState<LcuDirection>(LcuDirection.idle)
  const [dcuDirection, setDcuDirection] = useState<DcuDirection>(DcuDirection.idle)
  const [lcuTarget, setLcuTarget] = useState(0)
  const [dcuTarget, setDcuTarget] = useState(0)
  const [lcuDuration, setLcuDuration] = useState(5)
  const [dcuDuration, setDcuDuration] = useState(5)

  // Helper functions for value conversion and validation
  const validateLcuTarget = (value: number, mode: string) => {
    if (mode === "pid_speed") {
      // For PID speed mode, value is in mm/s
      return Math.max(0, value)
    } else {
      // For other modes, value is duty cycle percentage (0-100)
      return Math.min(Math.max(value, 0), 100)
    }
  }

  const validateDcuTarget = (value: number, mode: string) => {
    if (mode === "pid_speed") {
      // For PID speed mode, value is in RPM
      return Math.max(0, value)
    } else {
      // For other modes, value is voltage (0-24V)
      return Math.min(Math.max(value, 0), 24)
    }
  }

  // Update target setters to use validation
  const setLcuTargetWithValidation = (value: number) => {
    setLcuTarget(validateLcuTarget(value, lcuMode))
  }

  const setDcuTargetWithValidation = (value: number) => {
    setDcuTarget(validateDcuTarget(value, dcuMode))
  }

  useEffect(() => {
    websocket.onStatusChange((status) => {
      setWsConnected(status === "connected")
    })

    websocket.on("all", (data) => {
      console.log("Received WebSocket data:", data)
    })

    websocket.on("lcu_status", (lcuData) => {
      if (lcuData.mode) setLcuMode(String(lcuData.mode))
      if (lcuData.direction && lcuData.direction !== "idle") setLcuDirection(lcuData.direction as LcuDirection)
      if (mode === "manual") setManualStatus(lcuData.mode !== "idle" ? "running" : "stopped")
    })

    websocket.on("dcu_status", (dcuData) => {
      if (dcuData.mode) setDcuMode(String(dcuData.mode))
      if (dcuData.direction && dcuData.direction !== "idle") setDcuDirection(dcuData.direction as DcuDirection)
      if (mode === "manual" && manualStatus === "stopped") {
        setManualStatus(dcuData.mode !== "idle" ? "running" : "stopped")
      }
    })

    return () => {
      websocket.off("all", () => {})
      websocket.off("lcu_status", () => {})
      websocket.off("dcu_status", () => {})
    }
  }, [mode, manualStatus])

  const emergencyStop = async () => {
    try {
      // Call the emergency stop API
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const response = await apiClient.emergencyStop() as any

      if (response.success) {
        // Stop any active run or experiment
        if (currentRunId && selectedProjectId && selectedExperiment) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          await (apiClient.endRun as any)(selectedProjectId, selectedExperiment);
          setCurrentRunId(null);
        }
        
        // Update system status
        setSystemStatus("stopped");
        setExperimentStatus("stopped");
        setManualStatus("stopped");
        
        // Reset modes
        setLcuMode("idle");
        setDcuMode("idle");
        
        // Reset all sliders and inputs to 0
        setLcuTarget(0);
        setDcuTarget(0);
        setLcuDuration(0);
        setDcuDuration(0);
        setLcuDirection(LcuDirection.idle);
        setDcuDirection(DcuDirection.idle);
      } else {
        console.error("Failed to trigger emergency stop:", response.message);
      }
    } catch (error) {
      console.error("Error triggering emergency stop:", error);
    }
  }

  // Track which unit changed and if we're currently sending commands
  const [changedUnit, setChangedUnit] = useState<"lcu" | "dcu" | null>(null)
  const [isSendingCommand, setIsSendingCommand] = useState(false)

  // Update changedUnit and auto-set modes when LCU or DCU values change
  useEffect(() => {
    if (isSendingCommand) return; // Don't trigger if we're already sending a command

    if (lcuMode !== "idle" || lcuTarget !== 0 || lcuDirection !== LcuDirection.idle) {
      setChangedUnit("lcu")
      // Always set LCU mode to pid_speed
      setLcuMode("pid_speed")
    }
  }, [lcuMode, lcuTarget, lcuDirection, isSendingCommand])

  useEffect(() => {
    if (isSendingCommand) return; // Don't trigger if we're already sending a command

    if (dcuMode !== "idle" || dcuTarget !== 0 || dcuDirection !== DcuDirection.idle) {
      setChangedUnit("dcu")
      // Always set DCU mode to run_cont
      setDcuMode("run_cont")
    }
  }, [dcuMode, dcuTarget, dcuDirection, isSendingCommand])

  const sendCommand = async (unit: "lcu" | "dcu", command: number, params: any) => {
    if (isSendingCommand) return false; // Prevent multiple simultaneous sends
    
    try {
      setIsSendingCommand(true);
      
      // Validate and convert parameters based on unit and command
      let validatedParams = { ...params }
      
      if (unit === "lcu") {
        // For LCU, always use pid_speed mode
        validatedParams.pid_setpoint = Math.max(0, params.target ?? 0)
      } else if (unit === "dcu") {
        // For DCU, always use run_cont mode
        validatedParams.target = Math.min(Math.max(params.target ?? 0, 0), 24)
      }

      // Format command to match what the API expects
      const commandPayload = {
        device: unit,
        command: {
          mode: unit === "lcu" ? LcuCommand.pid_speed : DcuCommand.run_cont, // Force correct modes
          direction: validatedParams.direction ?? 0,
          target: validatedParams.target ?? 0,
          pid_setpoint: validatedParams.pid_setpoint ?? 0,
          duration: validatedParams.duration ?? 0,
          project_id: selectedProjectId || 0,
          experiment_id: selectedExperiment || 0,
          run_id: currentRunId || 0
        }
      }

      console.log(`Sending ${unit} command:`, commandPayload)
      const response = await (apiClient.sendCommand as any)(commandPayload)
      console.log(`${unit} command response:`, response)

      if (!response.success) {
        console.error(`Failed to send ${unit} command:`, response.message)
        return false
      }

      console.log(`Successfully sent ${unit} command:`, response.message)
      return true
    } catch (error) {
      console.error(`Error sending ${unit} command:`, error)
      return false
    } finally {
      setIsSendingCommand(false);
    }
  }

  // Only send command for the changed unit
  const executeCommand = async (unit: "lcu" | "dcu", command: number, params: any) => {
    if (isSendingCommand) return; // Prevent multiple simultaneous sends

    // Handle stop/idle commands
    if (command === LcuCommand.idle || command === DcuCommand.idle) {
      if (unit === "lcu") {
        setLcuMode("idle")
        await sendCommand("lcu", LcuCommand.idle, {})
      } else {
        setDcuMode("idle")
        await sendCommand("dcu", DcuCommand.idle, {})
      }
      return
    }

    // Only send commands when explicitly called through startManual or startExperiment
    if (systemStatus === "stopped" && (command === LcuCommand.pid_speed || command === DcuCommand.run_cont)) {
      // Only send both commands if this is the first command being sent
      if (unit === "lcu") {
        // Format LCU command exactly like DCU command
        const lcuCommand = {
          device: "lcu",
          command: {
            mode: LcuCommand.pid_speed,
            direction: lcuDirection,
            target: lcuTarget,
            pid_setpoint: 0,
            duration: 0,
            project_id: selectedProjectId || 0,
            experiment_id: selectedExperiment || 0,
            run_id: currentRunId || 0
          }
        }
        const dcuCommand = {
          device: "dcu",
          command: {
            mode: DcuCommand.run_cont,
            direction: dcuDirection,
            target: dcuTarget,
            pid_setpoint: 0,
            duration: 0,
            project_id: selectedProjectId || 0,
            experiment_id: selectedExperiment || 0,
            run_id: currentRunId || 0
          }
        }
        await (apiClient.sendCommand as any)(lcuCommand)
        await (apiClient.sendCommand as any)(dcuCommand)
      }
      return
    }
    
    // Otherwise only send the command for the changed unit
    if (unit === changedUnit) {
      // Format command exactly like DCU command
      const commandPayload = {
        device: unit,
        command: {
          mode: unit === "lcu" ? LcuCommand.pid_speed : DcuCommand.run_cont,
          direction: params.direction ?? 0,
          target: params.target ?? 0,
          pid_setpoint: 0,
          duration: 0,
          project_id: selectedProjectId || 0,
          experiment_id: selectedExperiment || 0,
          run_id: currentRunId || 0
        }
      }
      await (apiClient.sendCommand as any)(commandPayload)
    }
  }

  const startManual = async () => {
    try {
      // Send both LCU and DCU commands when starting
      await sendCommand("lcu", LcuCommand.pid_speed, { target: lcuTarget, direction: lcuDirection })
      await sendCommand("dcu", DcuCommand.run_cont, { target: dcuTarget, direction: dcuDirection })
      setSystemStatus("running")
    } catch (error) {
      console.error("Failed to start manual:", error)
    }
  }

  const startExperiment = async () => {
    if (!selectedProjectId || !selectedExperiment) {
      console.error("Cannot start experiment: Missing project or experiment", {
        selectedProjectId,
        selectedExperiment
      });
      return;
    }

    try {
      console.log("Starting experiment with:", {
        projectId: selectedProjectId,
        experimentId: selectedExperiment,
        lcuTarget,
        lcuDirection,
        dcuTarget,
        dcuDirection
      });
      
      // Create a new run in the database
      console.log("Creating run in database...");
      const runResponse = await apiClient.createRun(
        selectedProjectId,
        selectedExperiment,
        {
          run_name: `Run ${new Date().toISOString()}`,
          run_status: "running",
          run_params: {
            lcu_target: lcuTarget,
            lcu_direction: lcuDirection,
            dcu_target: dcuTarget,
            dcu_direction: dcuDirection
          }
        }
      );
      console.log("Run creation response:", runResponse);

      if (runResponse.run_id) {
        // Store the run ID for later use
        setCurrentRunId(runResponse.run_id);
        console.log("Set current run ID to:", runResponse.run_id);
        
        // Send both LCU and DCU commands when starting
        console.log("Sending LCU command...");
        await sendCommand("lcu", LcuCommand.pid_speed, { target: lcuTarget, direction: lcuDirection });
        console.log("Sending DCU command...");
        await sendCommand("dcu", DcuCommand.run_cont, { target: dcuTarget, direction: dcuDirection });
        
        // Update system status
        setSystemStatus("running");
        console.log("Experiment started successfully with run ID:", runResponse.run_id);
      } else {
        console.error("Failed to create run:", runResponse);
      }
    } catch (error) {
      console.error("Error starting experiment:", error);
    }
  };

  const stopExperiment = async () => {
    if (!selectedProjectId || !selectedExperiment) {
      console.error("Cannot stop experiment: Missing project or experiment", {
        selectedProjectId,
        selectedExperiment
      });
      return;
    }

    try {
      // Send idle commands to both LCU and DCU
      await sendCommand("lcu", LcuCommand.idle, {})
      await sendCommand("dcu", DcuCommand.idle, {})
      
      // Reset modes to idle
      setLcuMode("idle")
      setDcuMode("idle")
      
      // Only try to end the run if we have a currentRunId
      if (currentRunId) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const endRunResponse = await (apiClient.endRun as any)(selectedProjectId, selectedExperiment);

        if ((endRunResponse as any).success) {
          setCurrentRunId(null);
          console.log("Experiment run ended successfully");
        } else {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          console.log("Run end response:", (endRunResponse as any).message);
        }
      } else {
        console.log("No active run to end, just stopping the experiment");
      }
      
      // Always update the UI state
      setSystemStatus("stopped");
      console.log("Experiment stopped successfully");
    } catch (error) {
      console.error("Error stopping experiment:", error);
    }
  };

  const stopManual = async () => {
    try {
      // Send idle commands to both LCU and DCU
      await sendCommand("lcu", LcuCommand.idle, {})
      await sendCommand("dcu", DcuCommand.idle, {})
      // Reset modes to idle
      setLcuMode("idle")
      setDcuMode("idle")
      setSystemStatus("stopped")
    } catch (error) {
      console.error("Error stopping manual:", error)
    }
  }

  return {
    mode,
    setMode,
    systemStatus,
    wsConnected,
    selectedExperiment,
    setSelectedExperiment,
    experimentMetadata,
    lcuMode,
    setLcuMode,
    dcuMode,
    setDcuMode,
    lcuDirection,
    setLcuDirection,
    dcuDirection,
    setDcuDirection,
    lcuTarget,
    setLcuTarget,
    dcuTarget,
    setDcuTarget,
    lcuDuration,
    setLcuDuration,
    dcuDuration,
    setDcuDuration,
    emergencyStop,
    startExperiment,
    stopExperiment,
    startManual,
    stopManual,
    executeCommand,
    projects,
    selectedProjectId,
    setSelectedProjectId,
    experiments,
    experimentStatus,
  }
} 