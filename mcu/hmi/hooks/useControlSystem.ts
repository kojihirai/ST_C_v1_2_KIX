import { useState, useEffect } from "react"
import { websocket } from "@/lib/websocket"
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
      await sendCommand("lcu", LcuCommand.pid_speed, { target: lcuTarget, direction: lcuDirection });
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
      
      // Send stop commands to both devices
      console.log("Sending stop commands...")
      await sendCommand("lcu", LcuCommand.idle, {});
      await sendCommand("dcu", DcuCommand.idle, {});
      
      // Update system status
      setSystemStatus("stopped");
      setManualStatus("stopped");
      console.log("Manual mode stopped successfully");
    } catch (error) {
      console.error("Error stopping manual mode:", error);
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