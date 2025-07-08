#!/usr/bin/env python3
"""
Test script to verify MQTT command sending
"""
import json
import time
import paho.mqtt.client as mqtt

BROKER_IP = "192.168.2.1"
DEVICE_ID = "test_client"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        # Subscribe to device responses
        client.subscribe("lcu/data")
        client.subscribe("dcu/data")
        client.subscribe("lcu/error")
        client.subscribe("dcu/error")
    else:
        print(f"Failed to connect, return code: {rc}")

def on_message(client, userdata, msg):
    print(f"Received on {msg.topic}: {msg.payload.decode()}")

def test_commands():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(BROKER_IP, 1883, 60)
        client.loop_start()
        
        print("Testing LCU commands...")
        
        # Test 1: Stop LCU
        stop_cmd = {"mode": 0, "direction": 0, "target": 0}
        client.publish("lcu/cmd", json.dumps(stop_cmd))
        print("Sent LCU stop command")
        time.sleep(1)
        
        # Test 2: Start LCU forward
        forward_cmd = {"mode": 2, "direction": 2, "target": 5.0}
        client.publish("lcu/cmd", json.dumps(forward_cmd))
        print("Sent LCU forward command")
        time.sleep(2)
        
        # Test 3: Stop LCU
        client.publish("lcu/cmd", json.dumps(stop_cmd))
        print("Sent LCU stop command")
        time.sleep(1)
        
        print("Testing DCU commands...")
        
        # Test 4: Stop DCU
        client.publish("dcu/cmd", json.dumps(stop_cmd))
        print("Sent DCU stop command")
        time.sleep(1)
        
        # Test 5: Start DCU clockwise
        cw_cmd = {"mode": 2, "direction": 2, "target": 50}
        client.publish("dcu/cmd", json.dumps(cw_cmd))
        print("Sent DCU clockwise command")
        time.sleep(2)
        
        # Test 6: Stop DCU
        client.publish("dcu/cmd", json.dumps(stop_cmd))
        print("Sent DCU stop command")
        
        print("Test completed!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    test_commands() 