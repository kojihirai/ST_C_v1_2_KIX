import time
import json
import threading
import serial
import struct
import os
import paho.mqtt.client as mqtt

try:
    os.nice(-20)
except PermissionError:
    pass

BROKER_IP = "192.168.2.1"
DEVICE_ID = "sdu"
SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 6000000
PACKET_SIZE = 7  # 3 x int16 + 1 sync byte
SYNC_BYTE = b'\n'
AMP_SCALE = 100.0

class SensorController:
    def __init__(self):
        # MQTT setup
        self.client = mqtt.Client()
        self.client.connect(BROKER_IP, 1883, 60)
        self.client.loop_start()
        self.client.subscribe(f"{DEVICE_ID}/cmd")
        self.client.on_message = self.on_message

        # Metadata
        self.project_id = 0
        self.experiment_id = 0
        self.run_id = 0

        # Serial setup
        self.ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUD_RATE,
            timeout=0,
            write_timeout=0,
            inter_byte_timeout=None,
            exclusive=True
        )
        time.sleep(2)

        self.running = True
        threading.Thread(target=self.publish_status, daemon=True).start()

    def read_sensors(self):
        try:
            if self.ser.in_waiting >= PACKET_SIZE:
                data = self.ser.read(PACKET_SIZE)
                if len(data) == PACKET_SIZE and data[-1] == ord(SYNC_BYTE):
                    # Unpack as 3 signed int16s, ignoring the sync byte
                    raw_drill, raw_power, raw_linear = struct.unpack('<hhh', data[:-1])
                    # Ensure division is performed with float values
                    return {
                        "DRILL": float(raw_drill) / AMP_SCALE,
                        "POWER": float(raw_power) / AMP_SCALE,
                        "LINEAR": float(raw_linear) / AMP_SCALE
                    }
        except Exception as e:
            self.send_error(f"Sensor read error: {e}")
        return None

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            # Ensure all values are integers
            self.project_id = int(data.get("project_id", 0))
            self.experiment_id = int(data.get("experiment_id", 0))
            self.run_id = int(data.get("run_id", 0))
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            self.send_error(f"MQTT command error: {e}")
            # Reset to safe values on error
            self.project_id = 0
            self.experiment_id = 0
            self.run_id = 0

    def publish_status(self):
        while self.running:
            meas = self.read_sensors()
            if meas:
                try:
                    status = {
                        # "timestamp": time.monotonic(),
                        "DRILL_CURRENT": float(meas["DRILL"]),
                        "POWER_CURRENT": float(meas["POWER"]),
                        "LINEAR_CURRENT": float(meas["LINEAR"]),
                        "project_id": int(self.project_id),
                        "experiment_id": int(self.experiment_id),
                        "run_id": int(self.run_id)
                    }
                    self.client.publish(f"{DEVICE_ID}/data", json.dumps(status))
                except (ValueError, TypeError) as e:
                    self.send_error(f"Status publish error: {e}")
            time.sleep(0.2)

    def send_error(self, msg):
        try:
            err = {"timestamp": time.time(), "error": str(msg)}
            self.client.publish(f"{DEVICE_ID}/error", json.dumps(err))
            print("ERROR:", msg)
        except Exception as e:
            print(f"Error sending error message: {e}")

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
