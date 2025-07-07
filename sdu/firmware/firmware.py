import time
import json
import threading
import serial
import struct
import os
import paho.mqtt.client as mqtt
from collections import deque

try:
    os.nice(-20)
except PermissionError:
    pass

BROKER_IP = "192.168.2.1"
DEVICE_ID = "sdu"
SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 6000000
PACKET_SIZE = 7
SYNC_BYTE = b'\n'
AMP_SCALE = 100.0
BATCH_SIZE = 50

class SensorController:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.connect(BROKER_IP, 1883, 60)
        self.client.loop_start()
        self.client.subscribe(f"{DEVICE_ID}/cmd")
        self.client.on_message = self.on_message

        self.ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUD_RATE,
            timeout=0,
            write_timeout=0,
            inter_byte_timeout=None,
            exclusive=True
        )
        time.sleep(2)

        self.data_buffer = b''
        self.running = True
        threading.Thread(target=self.publish_status, daemon=True).start()

    def read_sensors(self):
        try:
            if self.ser.in_waiting > 0:
                self.data_buffer += self.ser.read(self.ser.in_waiting)
            
            while len(self.data_buffer) >= PACKET_SIZE:
                if len(self.data_buffer) >= PACKET_SIZE and self.data_buffer[PACKET_SIZE - 1] == ord(SYNC_BYTE):
                    packet = self.data_buffer[:PACKET_SIZE]
                    self.data_buffer = self.data_buffer[PACKET_SIZE:]
                    
                    raw_drill, raw_power, raw_linear = struct.unpack('<hhh', packet[:-1])
                    return {
                        "DRILL": float(raw_drill) / AMP_SCALE,
                        "POWER": float(raw_power) / AMP_SCALE,
                        "LINEAR": float(raw_linear) / AMP_SCALE
                    }
                else:
                    sync_pos = self.data_buffer.find(SYNC_BYTE)
                    if sync_pos == -1:
                        self.data_buffer = b''
                        break
                    else:
                        self.data_buffer = self.data_buffer[sync_pos + 1:]
            
            if len(self.data_buffer) > PACKET_SIZE * 10:
                self.data_buffer = self.data_buffer[-PACKET_SIZE:]
                
        except Exception as e:
            self.send_error(f"Sensor read error: {e}")
        return None

    def read_sensors_batch(self):
        """Read multiple packets at once like speed_test.py"""
        try:
            if self.ser.in_waiting >= PACKET_SIZE * BATCH_SIZE:
                data = self.ser.read(PACKET_SIZE * BATCH_SIZE)
                self.data_buffer += data
                
                while len(self.data_buffer) >= PACKET_SIZE:
                    if self.data_buffer[PACKET_SIZE - 1] == ord(SYNC_BYTE):
                        packet = self.data_buffer[:PACKET_SIZE]
                        self.data_buffer = self.data_buffer[PACKET_SIZE:]
                        
                        raw_drill, raw_power, raw_linear = struct.unpack('<hhh', packet[:-1])
                        return {
                            "DRILL": float(raw_drill) / AMP_SCALE,
                            "POWER": float(raw_power) / AMP_SCALE,
                            "LINEAR": float(raw_linear) / AMP_SCALE
                        }
                    else:
                        sync_pos = self.data_buffer.find(SYNC_BYTE)
                        if sync_pos == -1:
                            self.data_buffer = b''
                            break
                        self.data_buffer = self.data_buffer[sync_pos + 1:]
                
                if self.ser.in_waiting > 0:
                    self.data_buffer += self.ser.read(self.ser.in_waiting)
                    
            if len(self.data_buffer) > PACKET_SIZE * 20:
                self.data_buffer = self.data_buffer[-PACKET_SIZE:]
                
        except Exception as e:
            self.send_error(f"Batch sensor read error: {e}")
        return None

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            self.send_error(f"MQTT command error: {e}")

    def publish_status(self):
        last_publish_time = time.time()
        publish_interval = 0.01  # Publish every 10ms
        consecutive_failures = 0
        
        while self.running:
            try:
                meas = self.read_sensors_batch()
                if not meas:
                    meas = self.read_sensors()
                
                current_time = time.time()
                
                if meas:
                    consecutive_failures = 0
                    status = {
                        "DRILL_CURRENT": float(meas["DRILL"]),
                        "POWER_CURRENT": float(meas["POWER"]),
                        "LINEAR_CURRENT": float(meas["LINEAR"]),
                    }
                    
                    self.client.publish(f"{DEVICE_ID}/data", json.dumps(status))
                    last_publish_time = current_time
                    
                else:
                    consecutive_failures += 1
                    if current_time - last_publish_time > 0.1:
                        status = {
                            "DRILL_CURRENT": 0.0,
                            "POWER_CURRENT": 0.0,
                            "LINEAR_CURRENT": 0.0,
                        }
                        self.client.publish(f"{DEVICE_ID}/data", json.dumps(status))
                        last_publish_time = current_time
                        
                        if consecutive_failures > 100:
                            print(f"Warning: No sensor data for {consecutive_failures} cycles")
                            consecutive_failures = 0
                
                time.sleep(0.01)
                
            except Exception as e:
                self.send_error(f"Publish status error: {e}")
                time.sleep(0.01)

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
