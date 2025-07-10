import { useState, useEffect } from "react"
import { websocket } from "@/lib/polling-manager"
import { SystemMode, SystemStatus, LcuDirection, DcuDirection, LcuCommand, DcuCommand } from "@/lib/constants"
import apiClient from "@/lib/api-client"

export function useControlSystem() {
  const [mode, setMode] = useState<SystemMode>("manual")
  const [systemStatus, setSystemStatus] = useState<SystemStatus>("stopped")
  const [wsConnected, setWsConnected] = useState(false)

  const [manualStatus, setManualStatus] = useState<SystemStatus>("stopped")

  const [lcuMode, setLcuMode] = useState<string>("run_cont")
  const [dcuMode, setDcuMode] = useState<string>("run_cont")
  const [lcuDirection, setLcuDirection] = useState<LcuDirection>(LcuDirection.idle)
  const [dcuDirection, setDcuDirection] = useState<DcuDirection>(DcuDirection.idle)
  const [lcuTarget, setLcuTarget] = useState(0)
  const [dcuTarget, setDcuTarget] = useState(0)

  // Helper functions for value conversion and validation
  const validateLcuTarget = (value: number, mode: string) => {
    // For run_cont mode, value is duty cycle percentage (0-100)
    return Math.min(Math.max(value, 0), 100)
  }

  const validateDcuTarget = (value: number, mode: string) => {
    // For run_cont mode, value is voltage (0-24V)
    return Math.min(Math.max(value, 0), 24)
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

    // Handle device status updates from polling
    websocket.on("device_status_update", (data) => {
      console.log("Received device status update:", data)
      // Note: With polling, we only get overall device status, not individual device data
      // The system status will be managed by the start/stop commands instead
    })

    // Connect to start polling
    websocket.connect()

    return () => {
      websocket.off("device_status_update", () => {})
      websocket.disconnect()
    }
  }, [mode, manualStatus])

  const sendCommand = async (unit: "lcu" | "dcu", command: number, params: any) => {
    try {
      const commandParams = {
        mode: command,
        direction: params.direction || 0,
        target: params.target || 0
      }

      console.log(`Sending ${unit} command:`, commandParams)
      const response = await apiClient.sendCommand({
        device: unit,
        command: commandParams
      })

      if (response.success) {
        console.log(`${unit} command sent successfully`)
      } else {
        console.error(`${unit} command failed:`, response.message)
      }
    } catch (error) {
      console.error(`Error sending ${unit} command:`, error)
    }
  }

  const executeCommand = async (unit: "lcu" | "dcu", command: number, params: any) => {
    // Safety check: don't send commands if system is stopped
    if (systemStatus === "stopped" && command !== LcuCommand.idle && command !== DcuCommand.idle) {
      console.log(`Blocking ${unit} command - system is stopped`);
      return false;
    }
    
    try {
      const commandParams = {
        mode: command,
        direction: params.direction || 0,
        target: params.target || 0
      }

      console.log(`Executing ${unit} command:`, commandParams)
      const response = await apiClient.sendCommand({
        device: unit,
        command: commandParams
      })

      if (response.success) {
        console.log(`${unit} command executed successfully`)
        return true
      } else {
        console.error(`${unit} command failed:`, response.message)
        return false
      }
    } catch (error) {
      console.error(`Error executing ${unit} command:`, error)
      return false
    }
  }

  const startManual = async () => {
    try {
      console.log("Starting manual mode...")
      
      // Send both LCU and DCU commands when starting
      console.log("Sending LCU command...")
      await sendCommand("lcu", LcuCommand.run_cont, { target: lcuTarget, direction: lcuDirection });
      console.log("Sending DCU command...")
      await sendCommand("dcu", DcuCommand.run_cont, { target: dcuTarget, direction: dcuDirection });
      
      // Update system status
      setSystemStatus("running");
      setManualStatus("running");
      console.log("Manual mode started successfully");
    } catch (error) {
      console.error("Error starting manual mode:", error);
    }
  }

  const stopManual = async () => {
    try {
      console.log("Stopping manual mode...")
      
      // Immediately set system status to stopped for UI responsiveness
      setSystemStatus("stopped");
      setManualStatus("stopped");
      
      // Send immediate stop commands to both devices with retry logic
      const stopCommands = async () => {
        const promises = [
          sendCommand("lcu", LcuCommand.idle, {}),
          sendCommand("dcu", DcuCommand.idle, {})
        ];
        
        try {
          await Promise.allSettled(promises);
          console.log("Stop commands sent to both devices");
        } catch (error) {
          console.error("Error sending stop commands:", error);
          // Even if commands fail, we've already stopped the UI
        }
      };
      
      // Execute stop commands immediately
      stopCommands();
      
      console.log("Manual mode stopped successfully");
    } catch (error) {
      console.error("Error stopping manual mode:", error);
      // Ensure system is marked as stopped even if there's an error
      setSystemStatus("stopped");
      setManualStatus("stopped");
    }
  }

  return {
    // State
    mode,
    setMode,
    systemStatus,
    wsConnected,
    
    // Manual mode state
    manualStatus,
    lcuMode,
    setLcuMode,
    dcuMode,
    setDcuMode,
    lcuDirection,
    setLcuDirection,
    dcuDirection,
    setDcuDirection,
    lcuTarget,
    setLcuTarget: setLcuTargetWithValidation,
    dcuTarget,
    setDcuTarget: setDcuTargetWithValidation,
    
    // Functions
    sendCommand,
    executeCommand,
    startManual,
    stopManual
  }
} 