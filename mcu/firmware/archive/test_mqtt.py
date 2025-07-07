#!/usr/bin/env python3
"""
Test script to simulate MQTT messages from devices
This helps verify the device status monitoring functionality
"""

import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime

# MQTT Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

# Create MQTT client
client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")

def on_publish(client, userdata, mid):
    print(f"Message published with ID: {mid}")

# Set up callbacks
client.on_connect = on_connect
client.on_publish = on_publish

# Connect to broker
client.connect(MQTT_BROKER, MQTT_PORT)
client.loop_start()

def send_device_data(device, data_type="data"):
    """Send simulated device data or error"""
    topic = f"{device}/{data_type}"
    
    if data_type == "data":
        # Simulate device data
        payload = {
            "timestamp": datetime.now().isoformat(),
            "temperature": random.uniform(20, 30),
            "humidity": random.uniform(40, 60),
            "pressure": random.uniform(1000, 1020),
            "status": "operational"
        }
    else:
        # Simulate error
        payload = {
            "timestamp": datetime.now().isoformat(),
            "error_code": random.randint(1000, 9999),
            "error_message": f"Simulated error from {device}",
            "severity": random.choice(["warning", "error", "critical"])
        }
    
    message = json.dumps(payload)
    result = client.publish(topic, message)
    print(f"📤 Sent {data_type} to {topic}: {len(payload)} fields")
    return result

def main():
    devices = ["lcu", "dcu", "sdu"]
    
    print("🚀 Starting MQTT device simulation...")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            # Send data from random device
            device = random.choice(devices)
            
            # 90% chance of sending data, 10% chance of sending error
            if random.random() < 0.9:
                send_device_data(device, "data")
            else:
                send_device_data(device, "error")
            
            # Wait 2-5 seconds between messages
            time.sleep(random.uniform(2, 5))
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping MQTT simulation...")
        client.loop_stop()
        client.disconnect()
        print("✅ Simulation stopped")

if __name__ == "__main__":
    main() 