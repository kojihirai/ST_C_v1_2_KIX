import time
import json
import struct
import threading
import pigpio
import paho.mqtt.client as mqtt
from enum import Enum

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

BROKER_IP = "192.168.2.1"
DEVICE_ID = "dcu"
CONTACTOR_PIN = 27
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
            print("Failed to read torque")
            return None
        
    def read_rpm(self):
        result = self.read_parameter(0x02, 2, signed=True)
        if result is not None:
            return result
        else:
            print("Failed to read RPM")
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

class Mode(Enum):
    IDLE = 0
    RUN_CONTINUOUS = 2

class Direction(Enum):
    IDLE = 0
    ON = 1
    OFF = 2

# === Main Contactor Controller ===
class ContactorController:
    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.connect(BROKER_IP, 1883, 60)
        self.client.loop_start()
        self.client.subscribe(f"{DEVICE_ID}/cmd")
        self.client.on_message = self.on_message

        self.mode = Mode.IDLE
        self.direction = Direction.OFF

        # Initialize GPIO for contactor
        self.pi = pigpio.pi()
        self.pi.set_mode(CONTACTOR_PIN, pigpio.OUTPUT)
        self.pi.write(CONTACTOR_PIN, 0)  # Start with contactor OFF

        # Initialize torque sensor
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

        self.torque_value = 0.0
        self.rpm_value = 0.0

        self.running = True
        threading.Thread(target=self.run, daemon=True).start()
        threading.Thread(target=self.publish_status, daemon=True).start()

    def read_sensors(self):
        try:
            torque = self.torque_sensor.read_parameter(0x00, 2, signed=True)
            rpm = self.torque_sensor.read_parameter(0x02, 2, signed=True)
            
            if torque is not None:
                self.torque_value = torque / 10
            if rpm is not None:
                self.rpm_value = rpm/10
        except Exception as e:
            print(f"Sensor read error: {e}")

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            new_mode = Mode(data.get("mode", 0))
            new_direction = Direction(data.get("direction", 0))
            
            # If switching to IDLE, immediately turn off contactor
            if new_mode == Mode.IDLE:
                self.set_contactor(False)
                print("Immediate stop command received - contactor OFF")
            
            self.mode = new_mode
            self.direction = new_direction

            print(f"Received: Mode={self.mode.name}, Dir={self.direction.name}")
        except Exception as e:
            self.send_error(f"MQTT command error: {e}")

    def set_contactor(self, state):
        """Set contactor state: True for ON, False for OFF"""
        self.pi.write(CONTACTOR_PIN, 1 if state else 0)
        print(f"Contactor {'ON' if state else 'OFF'}")

    def run(self):
        while self.running:
            self.read_sensors()

            if self.mode == Mode.IDLE:
                self.set_contactor(False)
            elif self.mode == Mode.RUN_CONTINUOUS:
                if self.direction == Direction.ON:
                    self.set_contactor(True)
                else:
                    self.set_contactor(False)
            else:
                self.set_contactor(False)

            time.sleep(0.05)

    def publish_status(self):
        while self.running:
            contactor_state = self.pi.read(CONTACTOR_PIN)
            status = {
                "mode": self.mode.value,
                "direction": self.direction.value,
                "contactor_state": contactor_state,
                "rpm": round(self.rpm_value, 1),
                "torque": round(self.torque_value, 2),
            }
            self.client.publish(f"{DEVICE_ID}/data", json.dumps(status))
            time.sleep(0.2)

    def send_error(self, msg):
        error = {"timestamp": time.time(), "error": msg}
        self.client.publish(f"{DEVICE_ID}/error", json.dumps(error))
        print("ERROR:", msg)

    def stop(self):
        self.running = False
        self.client.loop_stop()
        self.set_contactor(False)  # Ensure contactor is OFF when stopping
        self.pi.stop()
        print("DCU stopped.")

if __name__ == "__main__":
    try:
        controller = ContactorController()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop()
