import { LcuDirection, DcuDirection } from "./constants"

interface LcuParams {
  target?: number
  direction?: LcuDirection
}

export function getLcuParams(mode: string, target: number, direction: LcuDirection): LcuParams {
  switch (mode) {
    case "run_cont":
      // For continuous mode, target is duty cycle percentage (0-100)
      return { target: Math.min(Math.max(target, 0), 100), direction: direction }
    default:
      return {}
  }
}

interface DcuParams {
  target?: number
  direction?: DcuDirection
}

export function getDcuParams(mode: string, target: number, direction: DcuDirection): DcuParams {
  switch (mode) {
    case "run_cont":
      // For continuous mode, target is voltage (0-24V)
      return { target: Math.min(Math.max(target, 0), 24), direction: direction }
    default:
      return {}
  }
} 