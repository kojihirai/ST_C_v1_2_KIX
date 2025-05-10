import { LcuDirection, DcuDirection } from "./constants"

interface LcuParams {
  target?: number
  direction?: LcuDirection
  duration?: number
  pid_setpoint?: number
}

export function getLcuParams(mode: string, target: number, direction: LcuDirection, duration: number): LcuParams {
  switch (mode) {
    case "run_dur":
      // For duration mode, target is duty cycle percentage (0-100)
      return { target: Math.min(Math.max(target, 0), 100), direction: direction, duration: duration }
    case "run_cont":
      // For continuous mode, target is duty cycle percentage (0-100)
      return { target: Math.min(Math.max(target, 0), 100), direction: direction }
    case "pid_pos":
    case "pid_current":
    case "pid_load":
    case "pid_speed":
      // For PID modes, target is in mm/s
      return { pid_setpoint: target, direction: direction }
    default:
      return {}
  }
}

interface DcuParams {
  target?: number
  direction?: DcuDirection
  duration?: number
  pid_setpoint?: number
}

export function getDcuParams(mode: string, target: number, direction: DcuDirection, duration: number): DcuParams {
  switch (mode) {
    case "run_dur":
      // For duration mode, target is voltage (0-24V)
      return { target: Math.min(Math.max(target, 0), 24), direction: direction, duration: duration }
    case "run_cont":
      // For continuous mode, target is voltage (0-24V)
      return { target: Math.min(Math.max(target, 0), 24), direction: direction }
    case "pid_speed":
    case "pid_current":
    case "pid_torque":
      // For PID modes, target is in RPM
      return { pid_setpoint: target, direction: direction }
    default:
      return {}
  }
} 