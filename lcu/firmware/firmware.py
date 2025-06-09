import time
import json
import threading
import struct
import csv
from enum import Enum
from queue import Queue

import paho.mqtt.client as mqtt
import pigpio

from LoadCell_Driver import LoadCellDriver  # updated import
from pymodbus.client import ModbusSerialClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder

# ----------------------------------------------------
# HighSpeedLogger Class (unchanged)
# ----------------------------------------------------
class HighSpeedLogger:
    def __init__(self, filename="lcu_highspeed_log.csv"):
        self.filename = filename
        self.file = open(self.filename, mode='w', newline='', buffering=1)
        self.csv_writer = csv.writer(self.file)
        self.csv_writer.writerow([
            "timestamp", "pos_ticks", "pos_mm", "pos_inches",
            "current", "load", "current_speed"
        ])
        self.queue = Queue(maxsize=100000)
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def log(self, data: dict):
        if not self.running:
            return
        try:
            self.queue.put_nowait(data)
        except:
            pass

    def _run(self):
        while self.running:
            record = self.queue.get()
            if record is None:
                break
            row = [
                record.get("timestamp", time.monotonic()),
                record.get("pos_ticks", 0),
                record.get("pos_mm", 0.0),
                record.get("pos_inches", 0.0),
                record.get("current", 0.0),
                record.get("load", 0.0),
                record.get("current_speed", 0.0)
            ]
            self.csv_writer.writerow(row)

    def stop(self):
        self.running = False
        self.queue.put(None)
        self.thread.join()
        self.file.close()


# ----------------------------------------------------
# PIDController, Enums, Constants (unchanged)
# ----------------------------------------------------
class PIDController:
    def __init__(self, kp, ki, kd, integral_limit=100.0, derivative_filter=0.1):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.integral_limit = integral_limit
        self.derivative_filter = derivative_filter
        self.reset()

    def compute(self, setpoint, measured):
        now = time.monotonic()
        dt = max(now - self.last_time, 1e-6)
        self.last_time = now

        error = setpoint - measured
        self.integral = max(min(self.integral + error * dt, self.integral_limit), -self.integral_limit)
        derivative = (error - self.prev_error) / dt
        filtered_d = (self.derivative_filter * derivative +
                      (1 - self.derivative_filter) * self.prev_derivative)
        output = self.kp * error + self.ki * self.integral + self.kd * filtered_d

        self.prev_error, self.prev_derivative = error, filtered_d
        return output

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_derivative = 0.0
        self.last_time = time.monotonic()


class Mode(Enum):
    IDLE = 0
    RUN_CONTINUOUS = 2
    PID_SPEED = 6
    HOMING = 8


class Direction(Enum):
    IDLE = 0
    FW = 2
    BW = 1


# MotorSystem constants
BROKER_IP       = "192.168.2.1"
DEVICE_ID       = "lcu"
MOTOR_PINS      = {"RPWM": 18, "LPWM": 19, "REN": 25, "LEN": 26}
ENC_A, ENC_B    = 20, 21
PULSES_PER_MM   = 33
HOMING_SPEED    = 50
HOMING_TIMEOUT  = 10.0
MAX_HOMING_RETRIES = 3
PID_UPDATE_INTERVAL = 0.001


# ----------------------------------------------------
# MotorSystem Class (with LoadCellDriver integration)
# ----------------------------------------------------
class MotorSystem:
    def __init__(self):
        # MQTT setup
        self.client = mqtt.Client()
        self.client.connect(BROKER_IP, 1883, 60)
        self.client.loop_start()
        self.client.subscribe(f"{DEVICE_ID}/cmd")
        self.client.on_message = self.on_message

        # State
        self.mode = Mode.IDLE
        self.direction = Direction.IDLE
        self.target = 0.0
        self.encoder_pos = 0
        self.last_encoder_pos = 0
        self.current_speed = 0.0
        self.is_homed = False
        self.homing_in_progress = False
        self.last_speed_time = time.monotonic()
        self.last_pid_update = 0.0
        self.state_lock = threading.Lock()

        # PID
        self.speed_pid = PIDController(2.0, 0.05, 0.2, 50.0, 0.2)

        # GPIO & Encoder
        self.pi = pigpio.pi()
        for pin in MOTOR_PINS.values():
            self.pi.set_mode(pin, pigpio.OUTPUT)
            self.pi.write(pin, 0)
        self.pi.write(MOTOR_PINS["REN"], 1)
        self.pi.write(MOTOR_PINS["LEN"], 1)

        self.pi.set_mode(ENC_A, pigpio.INPUT)
        self.pi.set_mode(ENC_B, pigpio.INPUT)
        self.pi.set_pull_up_down(ENC_A, pigpio.PUD_UP)
        self.pi.set_pull_up_down(ENC_B, pigpio.PUD_UP)
        self.pi.callback(ENC_A, pigpio.EITHER_EDGE, self._encoder_callback)
        self.pi.callback(ENC_B, pigpio.EITHER_EDGE, self._encoder_callback)

        # Load cell (using revised driver)
        self.load_cell = LoadCellDriver(
            port="/dev/ttyUSB0",
            baudrate=9600,
            parity='N',
            stopbits=1,
            bytesize=8,
            timeout=1,
            slave_id=1,
            scale_factor=100
        )
        if self.load_cell.connect():
            print("Load cell connected")
        else:
            print("Load cell connection failed")

        # Logger
        self.logger = HighSpeedLogger()

        # Main loops
        self.running = True
        threading.Thread(target=self.run_loop, daemon=True).start()
        threading.Thread(target=self.send_data_loop, daemon=True).start()

    def _encoder_callback(self, gpio, level, tick):
        A = self.pi.read(ENC_A)
        B = self.pi.read(ENC_B)
        delta = (-1 if gpio == ENC_A and A == B else 1) if gpio == ENC_A else (-1 if A != B else 1)
        self.encoder_pos += delta

    def control_motor(self, duty_percent, direction):
        duty = int(1_000_000 * max(min(duty_percent, 100), 0) / 100)
        self.pi.write(MOTOR_PINS["REN"], 1)
        self.pi.write(MOTOR_PINS["LEN"], 1)
        if direction == Direction.FW:
            self.pi.hardware_PWM(MOTOR_PINS["RPWM"], 20000, 0)
            self.pi.hardware_PWM(MOTOR_PINS["LPWM"], 20000, duty)
        elif direction == Direction.BW:
            self.pi.hardware_PWM(MOTOR_PINS["LPWM"], 20000, 0)
            self.pi.hardware_PWM(MOTOR_PINS["RPWM"], 20000, duty)
        else:
            self.pi.hardware_PWM(MOTOR_PINS["RPWM"], 20000, 0)
            self.pi.hardware_PWM(MOTOR_PINS["LPWM"], 20000, 0)

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            with self.state_lock:
                if 'mode' in data:
                    self.mode = Mode(data['mode'])
                if 'direction' in data:
                    self.direction = Direction(data['direction'])
                if 'target' in data:
                    self.target = float(data['target'])
            print(f"Cmd: mode={self.mode}, dir={self.direction}, tgt={self.target}")
        except Exception as e:
            print(f"MQTT parse error: {e}")

    def run_loop(self):
        while self.running:
            now = time.monotonic()
            dt = now - self.last_speed_time
            if dt > 0:
                delta = self.encoder_pos - self.last_encoder_pos
                self.current_speed = (delta / PULSES_PER_MM) / dt
                self.last_encoder_pos = self.encoder_pos
                self.last_speed_time = now

            with self.state_lock:
                mode, direction, tgt = self.mode, self.direction, self.target

            if mode == Mode.HOMING:
                self._do_homing()
            elif mode == Mode.PID_SPEED:
                if not self.is_homed:
                    print("ERROR: Not homed")
                    self.mode = Mode.IDLE
                elif now - self.last_pid_update >= PID_UPDATE_INTERVAL:
                    ref = tgt if direction == Direction.FW else -tgt
                    out = self.speed_pid.compute(ref, self.current_speed)
                    duty = abs(out)
                    dir_ = Direction.FW if out >= 0 else Direction.BW
                    self.control_motor(duty, dir_)
                    self.last_pid_update = now
            elif mode == Mode.RUN_CONTINUOUS:
                self.control_motor(tgt, direction)
            else:
                self.control_motor(0, Direction.IDLE)

            time.sleep(0.001)

    def _do_homing(self):
        if self.homing_in_progress:
            return
        self.homing_in_progress = True
        for attempt in range(MAX_HOMING_RETRIES):
            start_pos = self.encoder_pos
            still = 0
            t0 = time.monotonic()
            self.control_motor(HOMING_SPEED, Direction.BW)
            while time.monotonic() - t0 < HOMING_TIMEOUT:
                time.sleep(0.005)
                if abs(self.encoder_pos - start_pos) == 0:
                    still += 1
                else:
                    still = 0
                start_pos = self.encoder_pos
                if still >= 10:
                    break
            self.control_motor(0, Direction.IDLE)
            time.sleep(0.3)
            if still >= 10:
                self.encoder_pos = 0
                self.is_homed = True
                print("Homing complete")
                break
            else:
                print(f"Homing attempt {attempt+1} failed")
        else:
            print("Homing failed")
        self.homing_in_progress = False

    def send_data_loop(self):
        while self.running:
            pos_ticks = self.encoder_pos
            pos_mm    = pos_ticks / PULSES_PER_MM
            pos_in    = pos_mm / 25.4
            load_val  = 0.0
            try:
                # read two registers (signed), scaled by scale_factor
                load_val = self.load_cell.read_parameter(0x00, length=2, signed=True) or 0.0
            except Exception:
                pass

            data = {
                "timestamp": time.monotonic(),
                "pos_ticks": pos_ticks,
                "pos_mm": round(pos_mm, 3),
                "pos_inches": round(pos_in, 3),
                "current": 0.0,
                "load": load_val,
                "current_speed": round(self.current_speed, 3)
            }

            self.logger.log(data)
            self.client.publish(f"{DEVICE_ID}/data", json.dumps(data))
            print(f"Published: {data}")
            time.sleep(0.2)

    def stop(self):
        self.running = False
        self.control_motor(0, Direction.IDLE)
        self.logger.stop()
        self.client.loop_stop()
        self.pi.stop()
        self.load_cell.disconnect()


if __name__ == "__main__":
    system = MotorSystem()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        system.stop()
