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
BROKER_IP = "192.168.2.4"
DEVICE_ID = "sdu"

ADC_PINS = {
    "DRILL": 0,
    "POWER": 1,
    "LINEAR": 2,
    "VIN": 3
}
#Full Scale 5V
# Drill motor: IN0 - 20mv/A
# Power In: IN1 - 100mv/A
# Linear actuator: IN 2 -187.5 mV/A
# VIN IN3

# === Main Motor Controller ===
class SensorController:
    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.connect(BROKER_IP, 1883, 60)
        self.client.loop_start()
        self.client.subscribe(f"{DEVICE_ID}/cmd")
        self.client.on_message = self.on_message
        # Initialize IDs as integers with default value 0
        self.project_id = 0
        self.experiment_id = 0
        self.run_id = 0
        # Threads
        self.running = True
        threading.Thread(target=self.run, daemon=True).start()
        threading.Thread(target=self.publish_status, daemon=True).start()

    def read_sensors(self):
        try:
            pass
        except Exception as e:
            print(f"Sensor read error: {e}")

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            self.project_id = data.get("project_id", 0)
            self.experiment_id = data.get("experiment_id", 0)
            self.run_id = data.get("run_id", 0)
        except Exception as e:
            self.send_error(f"MQTT command error: {e}")

    def publish_status(self):
        while self.running:
            status = {
                "timestamp": time.monotonic(),
                "DRILL_CURRENT": 0,
                "POWER_CURRENT": 0,
                "LINEAR_CURRENT": 0,
                "VIN_VOLTAGE": 0
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
        print("SDU stopped.")

if __name__ == "__main__":
    try:
        controller = SensorController()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop()
