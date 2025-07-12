import time
import json
import threading
import struct
import csv
from enum import Enum
from queue import Queue

import paho.mqtt.client as mqtt
import pigpio

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

class LoadCellDriver:
    def __init__(self, port, baudrate, parity, stopbits, bytesize, timeout, slave_id, scale_factor=100):
        self.client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            parity=parity,
            stopbits=stopbits,
            bytesize=bytesize
        )
        self.slave_id = slave_id
        self.connected = False
        self.scale_factor = scale_factor

    def __del__(self):
        try:
            self.client.close()
        except:
            pass

    def connect(self):
        try:
            self.connected = self.client.connect()
            return self.connected
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False

    def disconnect(self):
        try:
            self.client.close()
            self.connected = False
            print("Successfully disconnected")
        except Exception as e:
            print(f"Failed to disconnect: {e}")

    def read_parameter(self, address, length=1, signed=False):
        """
        Reads `length` registers starting at `address`, unpacks as signed if requested,
        then divides by scale_factor to apply the 1/100 scaling.
        """
        if not self.connected:
            print("Not connected")
            return None

        try:
            response = self.client.read_holding_registers(address=address, count=length, slave=self.slave_id)
            if response.isError():
                print(f"Failed to read parameter at address {hex(address)}")
                return None
            # unpack raw value
            if length == 1:
                raw = response.registers[0]
                if signed:
                    raw = struct.unpack('>h', struct.pack('>H', raw))[0]
            else:  # length == 2
                raw = (response.registers[0] << 16) | response.registers[1]
                if signed:
                    raw = struct.unpack('>i', struct.pack('>I', raw))[0]

            scaled = raw * 10
            return scaled

        except ModbusException as e:
            print(f"ModbusException at {hex(address)}: {e}")
        except Exception as e:
            print(f"Unexpected error at {hex(address)}: {e}")
        return None

    def write_parameter(self, address, value):
        """
        Writes a single register. `value` should be the unscaled integer.
        """
        if not self.connected:
            print("Not connected")
            return False

        try:
            response = self.client.write_register(address, int(value), slave=self.slave_id)
            if response.isError():
                print(f"Failed to write {value} to {hex(address)}")
                return False
            print(f"Wrote {value} to {hex(address)}")
            return True

        except ModbusException as e:
            print(f"ModbusException at {hex(address)}: {e}")
        except Exception as e:
            print(f"Unexpected error at {hex(address)}: {e}")
        return False

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
        if abs(error) < ERROR_TOLERANCE:
            error = 0.0
            self.integral *= 0.90
        else:
            self.integral += error * dt

        self.integral = max(min(self.integral, INTEGRAL_MAX), INTEGRAL_MIN)
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
    HOMING = 8


class Direction(Enum):
    IDLE = 0
    BW = 1   # Backward
    FW = 2   # Forward


BROKER_IP           = "192.168.2.1"
DEVICE_ID           = "lcu"
MOTOR_PINS          = {"RPWM": 18, "LPWM": 19, "REN": 25, "LEN": 26}
ENC_A, ENC_B        = 20, 21
PULSES_PER_MM       = 110
PWM_FREQ           = 20000
SPEED_SAMPLE_INTERVAL_MS = 50
MAX_SPEED_MMPS     = 9.144
SPEED_WINDOW       = 10
INTEGRAL_MAX       = 5.0
INTEGRAL_MIN       = -5.0
DUTY_MIN           = 5.0
DUTY_MAX           = 100.0
ERROR_TOLERANCE    = 0.002
HOMING_SPEED       = 50
HOMING_TIMEOUT     = 15.0
MAX_HOMING_RETRIES = 3
PID_UPDATE_INTERVAL = 0.001

LOAD_X_OFFSET = 1.5195
LOAD_Y_OFFSET = -0.5699

class MotorSystem:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.connect(BROKER_IP, 1883, 60)
        self.client.loop_start()
        self.client.subscribe(f"{DEVICE_ID}/cmd")
        self.client.on_message = self.on_message

        self.mode = Mode.IDLE
        self.direction = Direction.IDLE
        self.target = 0.0
        self.encoder_pos = 0
        self.offset = 0
        self.last_encoder_pos = 0
        self.current_speed = 0.0
        self.is_homed = False
        self.homing_in_progress = False
        self.last_speed_time = time.monotonic()
        self.last_pid_update = 0.0
        self.state_lock = threading.Lock()
        self.tick_history = [0] * SPEED_WINDOW
        self.tick_index = 0

        self.speed_pid = PIDController(8.0, 1.0, 0.3, 50.0, 0.2)

        self.pi = pigpio.pi()
        for pin in MOTOR_PINS.values():
            self.pi.set_mode(pin, pigpio.OUTPUT)
            self.pi.write(pin, 0)

        self.pi.set_mode(ENC_A, pigpio.INPUT)
        self.pi.set_mode(ENC_B, pigpio.INPUT)
        self.pi.set_pull_up_down(ENC_A, pigpio.PUD_UP)
        self.pi.set_pull_up_down(ENC_B, pigpio.PUD_UP)
        self.pi.callback(ENC_A, pigpio.EITHER_EDGE, self._encoder_callback)
        self.pi.callback(ENC_B, pigpio.EITHER_EDGE, self._encoder_callback)

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

        # self.logger = HighSpeedLogger()

        self.running = True
        threading.Thread(target=self.run_loop, daemon=True).start()
        threading.Thread(target=self.send_data_loop, daemon=True).start()

    def _encoder_callback(self, gpio, level, tick):
        A = self.pi.read(ENC_A)
        B = self.pi.read(ENC_B)
        delta = 0

        if gpio == ENC_A:
            delta = -1 if A == B else 1
        elif gpio == ENC_B:
            delta = -1 if A != B else 1

        self.encoder_pos += delta

    def get_position_ticks(self):
        return self.encoder_pos - self.offset

    def get_speed_mmps(self, prev_ticks, new_ticks, dt_sec):
        return (new_ticks - prev_ticks) / PULSES_PER_MM / dt_sec

    def control_motor(self, duty_percent, direction):
        duty = int(1_000_000 * max(min(duty_percent, DUTY_MAX), DUTY_MIN) / 100)
        
        if duty > 0 and direction != Direction.IDLE:
            self.pi.write(MOTOR_PINS["REN"], 1)
            self.pi.write(MOTOR_PINS["LEN"], 1)
            
            if direction == Direction.FW:
                self.pi.hardware_PWM(MOTOR_PINS["RPWM"], PWM_FREQ, 0)
                self.pi.hardware_PWM(MOTOR_PINS["LPWM"], PWM_FREQ, duty)
            elif direction == Direction.BW:
                self.pi.hardware_PWM(MOTOR_PINS["LPWM"], PWM_FREQ, 0)
                self.pi.hardware_PWM(MOTOR_PINS["RPWM"], PWM_FREQ, duty)
        else:
            self.pi.write(MOTOR_PINS["REN"], 0)
            self.pi.write(MOTOR_PINS["LEN"], 0)

            self.pi.hardware_PWM(MOTOR_PINS["RPWM"], PWM_FREQ, 0)
            self.pi.hardware_PWM(MOTOR_PINS["LPWM"], PWM_FREQ, 0)


    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            with self.state_lock:
                if 'mode' in data:
                    new_mode = Mode(data['mode'])
                    # If switching to IDLE, immediately stop motor
                    if new_mode == Mode.IDLE:
                        self.control_motor(0, Direction.IDLE)
                        self.speed_pid.reset()  # Reset PID when stopping
                        print("Immediate stop command received - motor stopped and PID reset")
                    self.mode = new_mode
                if 'direction' in data:
                    self.direction = Direction(data['direction'])
                if 'target' in data:
                    self.target = float(data['target'])
            print(f"Cmd: mode={self.mode}, dir={self.direction}, tgt={self.target}")
        except Exception as e:
            print(f"MQTT parse error: {e}")

    def _do_homing(self):
        if self.homing_in_progress:
            return
        self.homing_in_progress = True
        print("=== Homing (retracting) ===")
        check_interval = 0.01
        required_still_cycles = 50
        still_counter = 0
        last_pos = self.encoder_pos
        start = time.time()

        self.control_motor(HOMING_SPEED, Direction.BW)

        while time.time() - start < HOMING_TIMEOUT:
            time.sleep(check_interval)
            curr_pos = self.encoder_pos
            delta = abs(curr_pos - last_pos)

            print(f"  Homing... encoder: {curr_pos} | delta: {delta}")
            if delta == 0:
                still_counter += 1
            else:
                still_counter = 0
            last_pos = curr_pos

            if still_counter >= required_still_cycles:
                print("Encoder stable — assuming hard stop.")
                break

        self.control_motor(0, Direction.IDLE)
        time.sleep(0.3)
        if abs(self.encoder_pos - last_pos) > 0:
            print("Movement detected after stop. Retrying...")
            self.homing_in_progress = False
            return self._do_homing()

        self.offset = self.encoder_pos
        print(f"[HOME] Final encoder ticks: {self.offset}")
        print("Homing complete. Encoder virtual zero set.")
        self.is_homed = True
        self.homing_in_progress = False

    def run_loop(self):
        while self.running:
            now = time.monotonic()
            dt = now - self.last_speed_time
            if dt > 0:
                curr_ticks = self.get_position_ticks()
                avg_speed = self.get_speed_mmps(self.tick_history[self.tick_index], curr_ticks, dt * SPEED_WINDOW)
                self.tick_history[self.tick_index] = curr_ticks
                self.tick_index = (self.tick_index + 1) % SPEED_WINDOW
                self.current_speed = avg_speed
                self.last_speed_time = now

            with self.state_lock:
                mode, direction, tgt = self.mode, self.direction, self.target

            # Debug: print current state every few seconds
            if int(now) % 5 == 0:  # Print every 5 seconds
                print(f"Run loop: mode={mode}, dir={direction}, tgt={tgt}")

            if mode == Mode.HOMING:
                self._do_homing()
            elif mode == Mode.RUN_CONTINUOUS:
                if not self.is_homed:
                    self._do_homing()
                elif now - self.last_pid_update >= PID_UPDATE_INTERVAL:
                    # Check if direction is IDLE first - if so, stop immediately
                    if direction == Direction.IDLE:
                        self.control_motor(0, Direction.IDLE)
                        self.speed_pid.reset()  # Reset PID to clear accumulated error
                        self.last_pid_update = now
                    else:
                        # Use the direction directly from the command
                        if direction == Direction.FW:
                            ref = tgt
                            dir_ = Direction.FW
                        elif direction == Direction.BW:
                            ref = -tgt
                            dir_ = Direction.BW
                        else:
                            ref = 0
                            dir_ = Direction.IDLE
                            self.speed_pid.reset()
                        
                        out = self.speed_pid.compute(ref, self.current_speed)
                        duty = abs(out)
                        # Force duty to 0 when direction is IDLE
                        if dir_ == Direction.IDLE:
                            duty = 0
                        self.control_motor(duty, dir_)
                        self.last_pid_update = now
            elif mode == Mode.IDLE:
                self.control_motor(0, Direction.IDLE)
                self.speed_pid.reset()  # Reset PID when in IDLE mode
                print("IDLE mode - motor stopped")
            else:
                self.control_motor(0, Direction.IDLE)

            time.sleep(0.01)

    def send_data_loop(self):
        while self.running:
            pos_ticks = self.encoder_pos
            pos_mm    = pos_ticks / PULSES_PER_MM
            # pos_in    = pos_mm / 25.4
            load_val  = 0.0
            try:
                load_val = self.load_cell.read_parameter(0x00, length=2, signed=True) or 0.0
                load_val = ((float(load_val)-LOAD_Y_OFFSET)/LOAD_X_OFFSET)
            except Exception:
                pass

            data = {
                "pos_ticks": pos_ticks,
                "pos_mm": round(pos_mm, 3),
                "load": load_val,
                "current_speed": round(self.current_speed, 3),
            }

            self.client.publish(f"{DEVICE_ID}/data", json.dumps(data))
            time.sleep(0.2)

    def stop(self):
        self.running = False
        self.control_motor(0, Direction.IDLE)
        # self.logger.stop()
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
