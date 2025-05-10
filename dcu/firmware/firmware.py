import time
import json
import struct
import threading
import pigpio
import board
import busio
import paho.mqtt.client as mqtt
from enum import Enum

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException
import time

# === Config ===
BROKER_IP = "192.168.2.1"
DEVICE_ID = "dcu"

MOTOR1_PINS = {"RPWM": 12, "LPWM": 13, "REN": 23, "LEN": 24}


# === Modbus Torque/RPM Sensor ===
class TorqueDriver:
    def __init__(self, port, baudrate, parity, stopbits, bytesize, timeout, slave_id):
        self.client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            parity=parity,
            stopbits=stopbits,
            bytesize=bytesize
        )
        self.slave_id = slave_id
        try:
            self.connected = self.client.connect()
        except Exception as e:
            print(f"Modbus connect error: {e}")
            self.connected = False

    def __del__(self):
        self.client.close()

    def read_torque(self):
        result = self.read_parameter(0x00, 2, signed=True)
        if result is not None:
            return result
        else:
            print("❌ Failed to read torque")
            return None
        
    def read_rpm(self):
        result = self.read_parameter(0x02, 2, signed=True)
        if result is not None:
            return result
        else:
            print("❌ Failed to read RPM")
            return None

    def read_parameter(self, address, length=1, signed=False):
        try:
            response = self.client.read_holding_registers(address=address, count=length, slave=self.slave_id)
            if not response.isError():
                if length == 1:
                    value = response.registers[0]
                    if signed:
                        value = struct.unpack('>h', struct.pack('>H', value))[0]
                elif length == 2:
                    value = (response.registers[0] << 16) | response.registers[1]
                    if signed:
                        value = struct.unpack('>i', struct.pack('>I', value))[0]
                return value
            else:
                print(f"Modbus read failed at {hex(address)}")
        except Exception as e:
            print(f"Modbus read exception at {hex(address)}: {e}")
        return None

# === Mode Definitions ===
class Mode(Enum):
    IDLE = 0
    RUN_CONTINUOUS = 2

class Direction(Enum):
    IDLE = 0
    CW = 1
    CCW = 2

# === PID Controller ===
class PIDController:
    def __init__(self, kp, ki, kd):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.integral = 0
        self.prev_error = 0

    def compute(self, setpoint, measured):
        error = setpoint - measured
        self.integral += error
        derivative = error - self.prev_error
        self.prev_error = error
        return self.kp * error + self.ki * self.integral + self.kd * derivative

# === Main Motor Controller ===
class MotorController:
    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.connect(BROKER_IP, 1883, 60)
        self.client.loop_start()
        self.client.subscribe(f"{DEVICE_ID}/cmd")
        self.client.on_message = self.on_message

        self.mode = Mode.IDLE
        self.direction = Direction.IDLE
        self.target = 50
        self.duration = 0
        self.pid_setpoint = 0

        self.torque_value = 0.0
        self.torque_offset = 0.0
        self.rpm_value = 0.0
        self.rpm_offset = 0.0

        # Initialize IDs as integers with default value 0
        self.project_id = 0
        self.experiment_id = 0
        self.run_id = 0

        # pigpio PWM setup
        self.pi = pigpio.pi()
        for pin in [MOTOR1_PINS["RPWM"], MOTOR1_PINS["LPWM"], MOTOR1_PINS["REN"], MOTOR1_PINS["LEN"]]:
            self.pi.set_mode(pin, pigpio.OUTPUT)
            self.pi.write(pin, 0)
        self.pi.write(MOTOR1_PINS["REN"], 1)
        self.pi.write(MOTOR1_PINS["LEN"], 1)

        # TorqueDriver (Modbus)
        self.torque_sensor = TorqueDriver(
            port="/dev/ttyACM0",
            baudrate=19200,
            parity="N",
            stopbits=1,
            bytesize=8,
            timeout=1,
            slave_id=1
        )
        if not self.torque_sensor.connected:
            self.send_error("Torque sensor failed to connect")
        
        self.state_lock = threading.Lock()

        # Threads
        self.running = True
        threading.Thread(target=self.run, daemon=True).start()
        threading.Thread(target=self.publish_status, daemon=True).start()

    def read_sensors(self):
        # Read torque and RPM in a single try-except block
        try:
            # Read both parameters at once to minimize Modbus communication
            torque = self.torque_sensor.read_parameter(0x00, 2, signed=True)
            rpm = self.torque_sensor.read_parameter(0x02, 2, signed=True)
            
            # Update values only if readings are valid
            if torque is not None:
                self.torque_value = (torque / 100.0) * 10
            if rpm is not None:
                self.rpm_value = rpm
        except Exception as e:
            # Log error but continue operation
            print(f"Sensor read error: {e}")

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            with self.state_lock:
                if "mode" in data:
                    self.mode = Mode(data["mode"])
                if "direction" in data:
                    self.direction = Direction(data["direction"])
                if "target" in data:
                    self.target = data["target"]
                if "duration" in data:
                    self.duration = data["duration"]
                if "pid_setpoint" in data:
                    self.pid_setpoint = data["pid_setpoint"]
                if "project_id" in data:
                    self.project_id = data["project_id"]
                if "experiment_id" in data:
                    self.experiment_id = data["experiment_id"]
                if "run_id" in data:
                    self.run_id = data["run_id"]
            print(f"Received: Mode={self.mode.name}, Dir={self.direction.name}, Speed={self.target}, Setpoint={self.pid_setpoint}")
        except Exception as e:
            self.send_error(f"MQTT command error: {e}")

    def set_motor(self, value, direction):
        pwm_val = int(min(max(abs(value), 0), 100) * 2.55)
        forward = value >= 0 if direction == Direction.CW else value < 0
        if forward:
            self.pi.set_PWM_dutycycle(MOTOR1_PINS["RPWM"], pwm_val)
            self.pi.set_PWM_dutycycle(MOTOR1_PINS["LPWM"], 0)
        else:
            self.pi.set_PWM_dutycycle(MOTOR1_PINS["RPWM"], 0)
            self.pi.set_PWM_dutycycle(MOTOR1_PINS["LPWM"], pwm_val)

    def stop_motor(self):
        self.pi.set_PWM_dutycycle(MOTOR1_PINS["RPWM"], 0)
        self.pi.set_PWM_dutycycle(MOTOR1_PINS["LPWM"], 0)

    def run(self):
        while self.running:
            with self.state_lock:
                mode = self.mode
                dir = self.direction
                targ = self.target


            self.read_sensors()

            if mode == Mode.IDLE:
                self.stop_motor()

            elif mode == Mode.RUN_CONTINUOUS:
                self.set_motor(targ, dir)
            
            else:
                pass

            time.sleep(0.05)

    def publish_status(self):
        while self.running:
            status = {
                "timestamp": time.monotonic(),
                "mode": self.mode.value,
                "direction": self.direction.value,
                "target": self.target,
                "setpoint": self.pid_setpoint,
                "rpm": round(self.rpm_value, 1),
                "torque": round(self.torque_value, 2),
                "project_id": self.project_id,
                "experiment_id": self.experiment_id,
                "run_id": self.run_id
            }
            self.client.publish(f"{DEVICE_ID}/data", json.dumps(status))
            print("Status:", status)
            time.sleep(0.2)

    def send_error(self, msg):
        error = {"timestamp": time.time(), "error": msg}
        self.client.publish(f"{DEVICE_ID}/error", json.dumps(error))
        print("ERROR:", msg)

    def stop(self):
        self.running = False
        self.client.loop_stop()
        self.stop_motor()
        self.pi.stop()
        print("DCU stopped.")

if __name__ == "__main__":
    try:
        controller = MotorController()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop()
