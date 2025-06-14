import time
import json
import threading
import serial

import paho.mqtt.client as mqtt

# === Config ===
BROKER_IP = "192.168.2.1"
DEVICE_ID = "sdu"
SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 115200

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

        # --- Serial setup ---
        self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Wait for serial connection to stabilize

        # Start background loops
        self.running = True
        threading.Thread(target=self.publish_status, daemon=True).start()

    def read_sensors(self):
        try:
            if self.ser.in_waiting:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    # Parse comma-separated values
                    drill, power, linear = map(float, line.split(','))
                    return {
                        "DRILL": drill,
                        "POWER": power,
                        "LINEAR": linear
                    }
            return None
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
        if self.ser.is_open:
            self.ser.close()
        print("SDU stopped.")

if __name__ == "__main__":
    try:
        controller = SensorController()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop()
