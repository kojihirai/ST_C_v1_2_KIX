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
SYNC_BYTE = 0x0A  # ord('\n')
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
        self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0, exclusive=True)
        time.sleep(2)

        # Preallocate buffer
        self.buffer = bytearray(PACKET_SIZE)
        self.view = memoryview(self.buffer)

        self.running = True
        threading.Thread(target=self.publish_status, daemon=True).start()

    def read_sensors(self):
        try:
            while self.ser.in_waiting >= PACKET_SIZE:
                self.ser.readinto(self.view)
                if self.buffer[-1] == SYNC_BYTE:
                    vals = struct.unpack_from('<hhh', self.view[:6])
                    return {
                        "DRILL": vals[0] / AMP_SCALE,
                        "POWER": vals[1] / AMP_SCALE,
                        "LINEAR": vals[2] / AMP_SCALE
                    }
        except Exception as e:
            self.send_error(f"Sensor read error: {e}")
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
        publish_topic = f"{DEVICE_ID}/data"
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
                self.client.publish(publish_topic, json.dumps(status), qos=0)
            # minimal delay, avoid hard sleep to allow tight loop
            time.sleep(0.0005)

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
