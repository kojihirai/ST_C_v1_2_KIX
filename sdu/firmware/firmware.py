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
REF = 4.880

ADC_PINS = {
    "DRILL": 0,
    "POWER": 1,
    "LINEAR": 2
}
# Full Scale 5V
# Drill motor: IN0 - 20mv/A
# Power In: IN1 - 100mv/A
# Linear actuator: IN 2 -187.5 mV/A

# === Main Motor Controller ===
class SensorController:
    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.connect(BROKER_IP, 1883, 60)
        self.client.loop_start()
        self.client.subscribe(f"{DEVICE_ID}/cmd")
        self.client.on_message = self.on_message

        self.project_id = 0
        self.experiment_id = 0
        self.run_id = 0

        self.running = True
        self.ADC = ADS1263.ADS1263()
        if (self.ADC.ADS1263_init_ADC1('ADS1263_400SPS') == -1):
            raise Exception("Failed to initialize ADC")
        
        # Configure ADC with explicit settings
        self.ADC.ADS1263_ConfigADC(
            ADS1263.ADS1263_GAIN['ADS1263_GAIN_1'],  # Gain = 1
            ADS1263.ADS1263_DRATE['ADS1263_400SPS']  # Data rate = 400 SPS
        )
        
        # Verify ADC configuration
        print("ADC Configuration:")
        print(f"Reference Voltage: {REF}V")
        print(f"Gain: 1")
        print(f"Data Rate: 400 SPS")
        
        self.ADC.ADS1263_SetMode(0)  # Single-ended mode
        threading.Thread(target=self.run, daemon=True).start()
        threading.Thread(target=self.publish_status, daemon=True).start()

    def run(self):
        """Main run loop for the controller"""
        while self.running:
            try:
                time.sleep(0.1)
            except Exception as e:
                self.send_error(f"Run loop error: {e}")
                time.sleep(1)

    def read_sensors(self):
        try:
            channel_list = list(ADC_PINS.values())
            adc_values = self.ADC.ADS1263_GetAll(channel_list)

            measurements = {}
            for sensor_name, channel in ADC_PINS.items():
                raw = adc_values[channel]
                print(f"Raw ADC value for {sensor_name}: {raw} (hex: {hex(raw)})")
                
                # Convert 24-bit ADC value to voltage
                # The ADS1263 is a 24-bit ADC with bipolar output
                # Full scale is ±VREF
                if raw & 0x800000:  # Check if bit 23 is set (negative value)
                    # Convert from two's complement
                    raw = raw - 0x1000000
                
                # Convert to voltage
                voltage = (raw * REF) / 0x800000
                
                print(f"Converted voltage for {sensor_name}: {voltage:.3f}V")

                if sensor_name == "DRILL":
                    current = voltage
                    measurements[sensor_name] = current
                elif sensor_name == "POWER":
                    current = voltage
                    measurements[sensor_name] = current
                elif sensor_name == "LINEAR":
                    current = voltage
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
        self.ADC.ADS1263_Exit()
        self.client.loop_stop()
        print("SDU stopped.")

if __name__ == "__main__":
    try:
        controller = SensorController()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop()
