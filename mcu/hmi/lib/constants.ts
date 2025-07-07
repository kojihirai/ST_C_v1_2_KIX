export enum LcuCommand {
  idle = 0,
  run_cont = 2,
  homing = 7,
}

export enum DcuCommand {
  idle = 0,
  run_cont = 2,
}

export enum LcuDirection {
  idle = 0,
  fw = 1,
  bw = 2,
}

export enum DcuDirection {
  idle = 0,
  cw = 1,
  ccw = 2,
}

export type SystemMode = "manual"
export type SystemStatus = "stopped" | "running" 