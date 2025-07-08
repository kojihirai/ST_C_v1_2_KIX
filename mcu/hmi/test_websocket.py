#!/usr/bin/env python3
"""
WebSocket test script to verify connection and message handling
"""
import asyncio
import websockets
import json
import time
from datetime import datetime

async def test_websocket():
    uri = "ws://localhost:8000/ws"
    
    try:
        print(f"Connecting to WebSocket: {uri}")
        async with websockets.connect(uri) as websocket:
            print("WebSocket connected successfully!")
            
            # Test 1: Send a simple message
            test_message = {"type": "test", "message": "Hello from test script"}
            await websocket.send(json.dumps(test_message))
            print(f"Sent: {test_message}")
            
            # Test 2: Request device status
            status_request = {"type": "request_status"}
            await websocket.send(json.dumps(status_request))
            print(f"Sent: {status_request}")
            
            # Listen for responses
            print("Listening for responses...")
            for i in range(10):  # Listen for 10 messages
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    print(f"Received: {response}")
                    
                    # Try to parse as JSON
                    try:
                        data = json.loads(response)
                        print(f"   Parsed: {json.dumps(data, indent=2)}")
                    except json.JSONDecodeError:
                        print(f"   Raw text: {response}")
                        
                except asyncio.TimeoutError:
                    print("Timeout waiting for message")
                    break
                    
    except websockets.exceptions.ConnectionRefused:
        print("Connection refused. Is the API server running on port 8000?")
    except Exception as e:
        print(f"WebSocket error: {e}")

async def test_websocket_with_mqtt():
    """Test WebSocket with simulated MQTT data"""
    uri = "ws://localhost:8000/ws"
    
    try:
        print(f"Connecting to WebSocket: {uri}")
        async with websockets.connect(uri) as websocket:
            print("WebSocket connected successfully!")
            
            # Simulate MQTT messages by sending them directly to the API
            import requests
            
            # Simulate LCU data
            lcu_data = {
                "mode": 0,
                "direction": 0,
                "target": 0,
                "rpm": 0.0,
                "torque": 0.0
            }
            
            response = requests.post("http://localhost:8000/send_command/", json={
                "device": "lcu",
                "command": {"mode": 2, "direction": 2, "target": 5.0}
            })
            print(f"Sent LCU command: {response.json()}")
            
            # Listen for WebSocket updates
            print("Listening for WebSocket updates...")
            for i in range(5):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    print(f"Received: {response}")
                except asyncio.TimeoutError:
                    print("Timeout waiting for message")
                    break
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("WebSocket Test Script")
    print("=" * 50)
    
    # Test basic WebSocket connection
    print("\n1. Testing basic WebSocket connection...")
    asyncio.run(test_websocket())
    
    print("\n" + "=" * 50)
    print("2. Testing WebSocket with MQTT integration...")
    try:
        asyncio.run(test_websocket_with_mqtt())
    except ImportError:
        print("requests library not available, skipping MQTT test")
    
    print("\nTest completed!") 