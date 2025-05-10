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

import RPi.GPIO as GPIO
import ADS1263

# === Config ===
BROKER_IP = "192.168.2.1"
DEVICE_ID = "sdu"
REF = 5.08  # Reference voltage for ADC

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
        # Initialize ADC
        self.ADC = ADS1263.ADS1263()
        if (self.ADC.ADS1263_init_ADC1('ADS1263_400SPS') == -1):
            raise Exception("Failed to initialize ADC")
        self.ADC.ADS1263_SetMode(0)  # 0 is singleChannel mode
        threading.Thread(target=self.run, daemon=True).start()
        threading.Thread(target=self.publish_status, daemon=True).start()

    def run(self):
        """Main run loop for the controller"""
        while self.running:
            try:
                # Main processing loop
                time.sleep(0.1)  # Small sleep to prevent CPU hogging
            except Exception as e:
                self.send_error(f"Run loop error: {e}")
                time.sleep(1)  # Longer sleep on error

    def read_sensors(self):
        try:
            channel_list = list(ADC_PINS.values())
            adc_values = self.ADC.ADS1263_GetAll(channel_list)

            measurements = {}
            for sensor_name, channel in ADC_PINS.items():
                raw = adc_values[channel]

                # Convert unsigned to signed 32-bit
                if raw & 0x80000000:
                    signed = raw - 0x100000000
                else:
                    signed = raw

                # Scale to voltage
                voltage = signed * REF / 0x7FFFFFFF

                # Convert voltage to current
                if sensor_name == "DRILL":
                    current = voltage / 0.020  # 20 mV/A
                elif sensor_name == "POWER":
                    current = voltage / 0.100  # 100 mV/A
                elif sensor_name == "LINEAR":
                    current = voltage / 0.1875  # 187.5 mV/A
                elif sensor_name == "VIN":
                    current = voltage  # direct voltage reading

                measurements[sensor_name] = current

            return measurements
        except Exception as e:
            print(f"Sensor read error: {e}")
            return None


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
            measurements = self.read_sensors()
            if measurements:
                status = {
                    "timestamp": time.monotonic(),
                    "DRILL_CURRENT": measurements["DRILL"],
                    "POWER_CURRENT": measurements["POWER"],
                    "LINEAR_CURRENT": measurements["LINEAR"],
                    "VIN_VOLTAGE": measurements["VIN"],
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
        self.ADC.ADS1263_Exit()  # Clean up ADC
        self.client.loop_stop()
        print("SDU stopped.")

if __name__ == "__main__":
    try:
        controller = SensorController()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop()
