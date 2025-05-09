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
      return { target: target, direction: direction, duration: duration }
    case "run_cont":
      return { target: target, direction: direction }
    case "pid_pos":
    case "pid_current":
    case "pid_load":
    case "pid_speed":
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
      return { target: target, direction: direction, duration: duration }
    case "run_cont":
      return { target: target, direction: direction }
    case "pid_speed":
    case "pid_current":
    case "pid_torque":
      return { pid_setpoint: target, direction: direction }
    default:
      return {}
  }
} 