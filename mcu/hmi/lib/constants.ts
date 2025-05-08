export enum LcuCommand {
  idle = 0,
  run_dur = 1,
  run_cont = 2,
  pid_pos = 3,
  pid_current = 4,
  pid_load = 5,
  pid_speed = 6,
  homing = 7,
}

export enum DcuCommand {
  idle = 0,
  run_dur = 1,
  run_cont = 2,
  pid_speed = 3,
  pid_current = 4,
  pid_torque = 5,
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

export type SystemMode = "manual" | "experiment"
export type SystemStatus = "stopped" | "running" 