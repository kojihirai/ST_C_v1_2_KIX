import time
import json
import threading

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

import paho.mqtt.client as mqtt

# === Config ===
BROKER_IP = "192.168.2.1"
DEVICE_ID = "sdu"

# ADS1115 channel → sensor mapping
ADC_CHANNELS = {
    "DRILL": ADS.P0,
    "POWER": ADS.P1,
    "LINEAR": ADS.P2
}

# Sensor conversion factors (V per A)
# Drill motor: 20 mV/A → 0.02 V/A
# Power In:     100 mV/A → 0.1 V/A
# Linear:       187.5 mV/A → 0.1875 V/A
CONVERSION = {
    "DRILL": 0.1,
    "POWER": 1,
    "LINEAR": 0.19125
}

class SensorController:
    def __init__(self):
        # --- MQTT setup ---
        self.client = mqtt.Client()
        self.client.connect(BROKER_IP, 1883, 60)
        self.client.loop_start()
        self.client.subscribe(f"{DEVICE_ID}/cmd")
        self.client.on_message = self.on_message

        # IDs that come in via MQTT cmd
        self.project_id = 0
        self.experiment_id = 0
        self.run_id = 0

        # --- ADS1115 setup ---
        i2c = busio.I2C(board.SCL, board.SDA)
        self.ads = ADS.ADS1115(i2c)
        # Optional: pick a gain if you need better range/precision
        # self.ads.gain = 1

        # Create one AnalogIn per sensor
        self.channels = {
            name: AnalogIn(self.ads, pin)
            for name, pin in ADC_CHANNELS.items()
        }

        # Start background loops
        self.running = True
        threading.Thread(target=self.publish_status, daemon=True).start()

    def read_sensors(self):
        measurements = {}
        try:
            for name, chan in self.channels.items():
                voltage = chan.voltage  # in volts
                current = voltage / CONVERSION[name]
                measurements[name] = current
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
            meas = self.read_sensors()
            if meas:
                status = {
                    "timestamp": time.monotonic(),
                    "DRILL_CURRENT": meas["DRILL"],
                    "POWER_CURRENT": meas["POWER"],
                    "LINEAR_CURRENT": meas["LINEAR"],
                    "project_id": self.project_id,
                    "experiment_id": self.experiment_id,
                    "run_id": self.run_id
                }
                self.client.publish(f"{DEVICE_ID}/data", json.dumps(status))
                print("Status:", status)
            time.sleep(0.2)

    def send_error(self, msg):
        err = {"timestamp": time.time(), "error": msg}
        self.client.publish(f"{DEVICE_ID}/error", json.dumps(err))
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
