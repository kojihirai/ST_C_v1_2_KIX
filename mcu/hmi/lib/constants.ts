export enum LcuCommand {
  idle = 0,
  run_cont = 2,
  homing = 8,
}

export enum DcuCommand {
  idle = 0,
  run_cont = 2,
}

export enum LcuDirection {
  idle = 0,
  bw = 1,  // Backward
  fw = 2,  // Forward
}

export enum DcuDirection {
  idle = 0,
  off = 2,  // Contactor OFF (Stop/Pause)
  on = 1,   // Contactor ON
}

export type SystemMode = "manual"
export type SystemStatus = "stopped" | "running" 