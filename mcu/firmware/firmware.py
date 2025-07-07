from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import asyncpg
import psycopg2
import psycopg2.extras
import json
import asyncio
import signal
import paho.mqtt.client as mqtt
import time

class CommandRequest(BaseModel):
    device: str
    command: dict

class DeviceStatus(BaseModel):
    device: str
    status: str  # "online", "offline", "warning"
    last_seen: Optional[datetime]
    data_count: int


app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://mcu.local:3001",
    "http://10.147.18.184:3001",
    "http://10.147.18.184:8000",
    "http://192.168.2.1:3001",
    "http://102.168.2.10:3001"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# --- Runtime State ---

device_data = {}
expected_devices = ["lcu", "dcu", "sdu"]
active_clients = []

# Device monitoring state
device_status = {}
monitoring_task = None


# --- Device Monitoring ---

def initialize_device_status():
    """Initialize status for all expected devices"""
    for device in expected_devices:
        device_status[device] = DeviceStatus(
            device=device,
            status="offline",
            last_seen=None,
            data_count=0
        )

def update_device_status(device: str, data: dict):
    """Update device status when data is received"""
    if device not in device_status:
        return
    
    current_time = datetime.now()
    device_status[device].last_seen = current_time
    device_status[device].data_count += 1
    
    # Update status to online
    previous_status = device_status[device].status
    if device_status[device].status != "online":
        device_status[device].status = "online"
        print(f"Device {device} is now ONLINE")
    

    
    # Trigger immediate broadcast if status changed
    if previous_status != device_status[device].status:
        asyncio.create_task(broadcast_device_status())

def check_device_health():
    """Check if devices are still sending data within expected intervals"""
    current_time = datetime.now()
    
    for device in expected_devices:
        if device not in device_status:
            continue
            
        status = device_status[device]
        last_seen = status.last_seen
        
        if last_seen is None:
            continue
            
        # Calculate expected interval (default to 30 seconds)
        expected_interval = 30
        warning_threshold = expected_interval * 1.5  # 50% grace period
        offline_threshold = expected_interval * 2    # 100% grace period
        
        time_since_last = (current_time - last_seen).total_seconds()
        
        if time_since_last > offline_threshold:
            if status.status != "offline":
                status.status = "offline"
                print(f"Device {device} is OFFLINE (no data for {time_since_last:.1f}s)")
                asyncio.create_task(broadcast_device_status())
        elif time_since_last > warning_threshold:
            if status.status != "warning":
                status.status = "warning"
                print(f"Device {device} is WARNING (no data for {time_since_last:.1f}s)")
                asyncio.create_task(broadcast_device_status())

async def monitoring_loop():
    """Background task to continuously monitor device health"""
    last_broadcast = 0
    broadcast_interval = 10  # Broadcast status every 10 seconds
    
    while True:
        try:
            current_time = time.time()
            
            # Check device health
            check_device_health()
            
            # Broadcast status updates periodically
            if current_time - last_broadcast >= broadcast_interval:
                await broadcast_device_status()
                last_broadcast = current_time
            
            await asyncio.sleep(5)  # Check every 5 seconds
        except Exception as e:
            print(f"Error in monitoring loop: {e}")
            await asyncio.sleep(5)

# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_clients.append(websocket)
    
    # Send initial device status
    initial_status = {
        "type": "device_status_update",
        "data": {
            "devices": [status.dict() for status in device_status.values()],
            "timestamp": datetime.now().isoformat()
        }
    }
    await websocket.send_text(json.dumps(initial_status))
    
    try:
        while True:
            message = await websocket.receive_text()
            print(f"Received: {message}")
            
            # Handle different message types
            try:
                data = json.loads(message)
                if data.get("type") == "request_status":
                    # Send current device status
                    status_response = {
                        "type": "device_status_update",
                        "data": {
                            "devices": [status.dict() for status in device_status.values()],
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    await websocket.send_text(json.dumps(status_response))
                else:
                    # Echo back other messages
                    await websocket.send_text(f"Server Response: {message}")
            except json.JSONDecodeError:
                # Handle plain text messages
                await websocket.send_text(f"Server Response: {message}")
                
    except WebSocketDisconnect:
        print("Client disconnected")
    finally:
        active_clients.remove(websocket)

# --- MQTT Setup ---

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
mqtt_client = mqtt.Client()

def on_mqtt_message(client, userdata, message):
    """Handle incoming MQTT messages"""
    try:
        print(f"MQTT message received on topic: {message.topic}")
        payload = json.loads(message.payload.decode())
        device = message.topic.split('/')[0]
        if device in expected_devices:
            device_data[device] = payload
            # Update device status when data is received
            update_device_status(device, payload)
            print(f"Updated status for device: {device}")
        else:
            print(f"Unknown device in topic: {device}")
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

def on_mqtt_connect(client, userdata, flags, rc):
    """Handle MQTT connection"""
    if rc == 0:
        print("Connected to MQTT broker")
        # Subscribe to all device topics
        for device in expected_devices:
            # Subscribe to any topic that starts with the device name
            client.subscribe(f"{device}/#")
            print(f"Subscribed to {device}/#")
    else:
        print(f"Failed to connect to MQTT broker, return code: {rc}")

mqtt_client.on_message = on_mqtt_message
mqtt_client.on_connect = on_mqtt_connect
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
mqtt_client.loop_start()

@app.post("/send_command/")
async def send_command(payload: CommandRequest):
    if payload.device not in expected_devices:
        return {"success": False, "message": "Invalid device"}

    command_with_ids = {
        **payload.command,
    }   

    mqtt_client.publish(f"{payload.device}/cmd", json.dumps(command_with_ids))
    return {"success": True, "message": f"Command sent to {payload.device}"}

# --- API Endpoints for Device Monitoring ---

@app.get("/device_status/")
async def get_device_status():
    """Get status of all devices"""
    return {
        "devices": [status.dict() for status in device_status.values()],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/device_status/{device}")
async def get_single_device_status(device: str):
    """Get status of a specific device"""
    if device not in device_status:
        raise HTTPException(status_code=404, detail="Device not found")
    return device_status[device].dict()

@app.get("/device_health/")
async def get_device_health_summary():
    """Get a summary of device health"""
    online_count = sum(1 for status in device_status.values() if status.status == "online")
    warning_count = sum(1 for status in device_status.values() if status.status == "warning")
    offline_count = sum(1 for status in device_status.values() if status.status == "offline")
    
    return {
        "summary": {
            "total_devices": len(expected_devices),
            "online": online_count,
            "warning": warning_count,
            "offline": offline_count
        },
        "devices": {device: status.dict() for device, status in device_status.items()},
        "timestamp": datetime.now().isoformat()
    }



# --- WebSocket Updates for Device Status ---

async def broadcast_device_status():
    """Broadcast device status updates to all connected WebSocket clients"""
    if not active_clients:
        return
    
    status_update = {
        "type": "device_status_update",
        "data": {
            "devices": [status.dict() for status in device_status.values()],
            "timestamp": datetime.now().isoformat()
        }
    }
    
    message = json.dumps(status_update)
    disconnected_clients = []
    
    for client in active_clients:
        try:
            await client.send_text(message)
        except Exception as e:
            print(f"Error sending to client: {e}")
            disconnected_clients.append(client)
    
    # Remove disconnected clients
    for client in disconnected_clients:
        if client in active_clients:
            active_clients.remove(client)

# --- Startup & Shutdown ---

@app.on_event("startup")
async def startup():
    global monitoring_task
    initialize_device_status()
    monitoring_task = asyncio.create_task(monitoring_loop())
    print("Device monitoring started")

@app.on_event("shutdown")
async def shutdown():
    global monitoring_task
    if monitoring_task:
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
    print("Device monitoring stopped")

def signal_handler(sig, frame):
    print("\nKeyboard Interrupt detected! Shutting down gracefully...")
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

def main():
    import uvicorn
    signal.signal(signal.SIGINT, signal_handler)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")

if __name__ == "__main__":
    main()
