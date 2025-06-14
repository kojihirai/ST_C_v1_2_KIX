import time
import json
import threading
import serial
import struct
import os
import paho.mqtt.client as mqtt

# Set process priority to maximum (optional, needs sudo)
try:
    os.nice(-20)
except PermissionError:
    pass  # Not fatal if not run with sudo

# === Config ===
BROKER_IP = "192.168.2.1"
DEVICE_ID = "sdu"
SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 6000000  # Updated to match teensy.ino
PACKET_SIZE = 7  # 3 x int16 + 1 sync byte
SYNC_BYTE = b'\n'
AMP_SCALE = 100.0  # Integer was scaled by 100 (0.01A resolution)

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
        self.ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUD_RATE,
            timeout=0,
            write_timeout=0,
            inter_byte_timeout=None,
            exclusive=True
        )
        time.sleep(2)  # Wait for serial connection to stabilize

        # Start background loops
        self.running = True
        threading.Thread(target=self.publish_status, daemon=True).start()

    def read_sensors(self):
        try:
            if self.ser.in_waiting >= PACKET_SIZE:
                data = self.ser.read(PACKET_SIZE)
                if len(data) == PACKET_SIZE and data[-1] == ord(SYNC_BYTE):
                    # Unpack as 3 signed int16s, ignoring the sync byte
                    raw_drill, raw_power, raw_linear = struct.unpack('<hhh', data[:-1])
                    return {
                        "DRILL": raw_drill / AMP_SCALE,
                        "POWER": raw_power / AMP_SCALE,
                        "LINEAR": raw_linear / AMP_SCALE
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
            time.sleep(0.001)  # Reduced sleep time for higher sampling rate

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
