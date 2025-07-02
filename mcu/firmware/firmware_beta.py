from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime
import asyncpg
import psycopg2
import psycopg2.extras
import json
import os
import asyncio
import signal
import threading
import cv2
import paho.mqtt.client as mqtt

# --- Video Recorder ---
class VideoRecorder:
    def __init__(self, save_dir="/media/pi/USB", fps=20, resolution=(640, 480)):
        self.save_dir = save_dir
        self.fps = fps
        self.resolution = resolution
        self.out = None
        self.cap = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.filename = None

    def _record(self, filename):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.out = cv2.VideoWriter(filename, fourcc, self.fps, self.resolution)

        while self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                self.out.write(frame)
            else:
                break

        self._cleanup()

    def _cleanup(self):
        if self.out:
            self.out.release()
        if self.cap:
            self.cap.release()

    def start(self, run_id):
        with self.lock:
            if self.running:
                return
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(self.save_dir, f"run_{run_id}_{timestamp}.avi")
            self.running = True
            self.filename = filename
            self.thread = threading.Thread(target=self._record, args=(filename,))
            self.thread.start()

    def stop(self):
        with self.lock:
            if not self.running:
                return None
            self.running = False
            if self.thread:
                self.thread.join()
            return self.filename

video_recorder = VideoRecorder()

# --- Models ---
class CommandRequest(BaseModel):
    device: str
    command: dict

class RunEndRequest(BaseModel):
    status: str = None
    notes: str = None

class RunCreate(BaseModel):
    run_name: str
    run_status: str
    run_description: Optional[str] = None
    run_params: Optional[dict] = None
    start_time: Optional[datetime] = None
    stop_time: Optional[datetime] = None

# --- FastAPI Setup ---
app = FastAPI()

origins = [
    "http://localhost:3000", "http://localhost:3001",
    "http://127.0.0.1:3000", "http://127.0.0.1:3001",
    "http://mcu.local:3001", "http://10.147.18.184:3001",
    "http://10.147.18.184:8000", "http://192.168.2.1:3001",
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

# --- DB Setup ---
DATABASE_URL = "postgresql://dune:dune1234@localhost:5432/data_mgmt"
db_pool = None

def get_conn():
    return psycopg2.connect(host="localhost", database="data_mgmt", user="dune", password="dune1234")

async def get_db():
    return await db_pool.acquire()

# --- Runtime State ---
device_data = {}
expected_devices = ["lcu", "dcu", "sdu"]
active_clients = []

# Device status tracking
device_status = {
    "lcu": {"status": "disconnected", "last_seen": None, "error": None},
    "dcu": {"status": "disconnected", "last_seen": None, "error": None},
    "sdu": {"status": "disconnected", "last_seen": None, "error": None}
}

current_run_info = {
    "run_id": 0,
    "experiment_id": 0,
    "project_id": 0
}

# --- MQTT ---
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
mqtt_client = mqtt.Client()

def on_mqtt_message(client, userdata, message):
    try:
        topic = message.topic
        payload = json.loads(message.payload.decode())
        topic_parts = topic.split("/")
        device = topic_parts[0]
        msg_type = topic_parts[1] if len(topic_parts) > 1 else ""
        
        if device in expected_devices:
            current_time = datetime.now()
            
            if msg_type == "data":
                # Update device data and status
                device_data[device] = payload
                device_status[device]["status"] = "connected"
                device_status[device]["last_seen"] = current_time
                device_status[device]["error"] = None
                
                print(f"✅ Data received from {device}: {len(payload)} fields")
                
            elif msg_type == "error":
                # Update device error status
                device_status[device]["status"] = "error"
                device_status[device]["error"] = payload
                device_status[device]["last_seen"] = current_time
                
                print(f"🚨 Error from {device}: {payload}")
            
            # Send status update to all connected WebSocket clients
            status_update = {
                "type": "device_status",
                "data": {
                    "devices": device_status,
                    "timestamp": current_time.isoformat()
                }
            }
            
            # Send to all active WebSocket clients
            for client in active_clients[:]:  # Copy list to avoid modification during iteration
                try:
                    asyncio.create_task(client.send_text(json.dumps(status_update)))
                except Exception as e:
                    print(f"⚠️ WebSocket Send Error: {e}")
                    active_clients.remove(client)
                    
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

mqtt_client.on_message = on_mqtt_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)

# Subscribe to all relevant endpoints for each device
for device in expected_devices:
    mqtt_client.subscribe(f"{device}/data")
    mqtt_client.subscribe(f"{device}/error")
    print(f"📡 Subscribed to {device}/data and {device}/error")

mqtt_client.loop_start()

# --- WebSocket ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db=Depends(get_db)):
    await websocket.accept()
    active_clients.append(websocket)
    
    # Send initial device status to the new client
    initial_status = {
        "type": "device_status",
        "data": {
            "devices": device_status,
            "timestamp": datetime.now().isoformat()
        }
    }
    await websocket.send_text(json.dumps(initial_status))
    
    try:
        while True:
            message = await websocket.receive_text()
            print(f"Received: {message}")
            await websocket.send_text(f"Server Response: {message}")
    except WebSocketDisconnect:
        print("Client disconnected")
    finally:
        active_clients.remove(websocket)
        await db_pool.release(db)

# --- Send Command with Video Trigger ---
@app.post("/send_command/")
async def send_command(payload: CommandRequest):
    if payload.device not in expected_devices:
        return {"success": False, "message": "Invalid device"}

    run_id = current_run_info["run_id"]
    device = payload.device
    command = payload.command

    command_with_ids = {
        **command,
        "project_id": current_run_info["project_id"] or 0,
        "experiment_id": current_run_info["experiment_id"] or 0,
        "run_id": run_id or 0
    }

    prev_mode = device_data.get(device, {}).get("mode", 0)
    new_mode = command.get("mode", prev_mode)

    if prev_mode == 0 and new_mode != 0:
        print(f"Starting video recording for run {run_id}")
        video_recorder.start(run_id)

    elif prev_mode != 0 and new_mode == 0:
        print(f"Stopping video recording for run {run_id}")
        video_path = video_recorder.stop()
        if video_path:
            print(f"Video saved to {video_path}")

    mqtt_client.publish(f"{device}/cmd", json.dumps(command_with_ids))
    return {"success": True, "message": f"Command sent to {device}"}

# --- Startup/Shutdown ---
@app.on_event("startup")
async def startup():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    
    # Start background device status check
    asyncio.create_task(check_device_status())
    print("🚀 Firmware started with device status monitoring")

@app.on_event("shutdown")
async def shutdown():
    await db_pool.close()
    if video_recorder.running:
        print("Graceful shutdown: stopping video...")
        video_recorder.stop()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

# --- Signal Handling ---
def signal_handler(sig, frame):
    print("\nKeyboard Interrupt detected! Shutting down gracefully...")
    asyncio.get_event_loop().create_task(shutdown())

# --- Background Tasks ---
async def check_device_status():
    """Periodically check device status and mark as disconnected if no recent data"""
    while True:
        try:
            current_time = datetime.now()
            status_changed = False
            
            for device in expected_devices:
                last_seen = device_status[device]["last_seen"]
                if last_seen:
                    # Mark as disconnected if no data for more than 10 seconds
                    time_diff = (current_time - last_seen).total_seconds()
                    if time_diff > 10 and device_status[device]["status"] != "disconnected":
                        device_status[device]["status"] = "disconnected"
                        device_status[device]["error"] = "No data received recently"
                        status_changed = True
                        print(f"⚠️ {device} marked as disconnected (no data for {time_diff:.1f}s)")
            
            # Send status update if any device status changed
            if status_changed and active_clients:
                status_update = {
                    "type": "device_status",
                    "data": {
                        "devices": device_status,
                        "timestamp": current_time.isoformat()
                    }
                }
                
                for client in active_clients[:]:
                    try:
                        await client.send_text(json.dumps(status_update))
                    except Exception as e:
                        print(f"⚠️ WebSocket Send Error: {e}")
                        active_clients.remove(client)
            
            await asyncio.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            print(f"Error in device status check: {e}")
            await asyncio.sleep(5)

# --- API Endpoints ---
@app.get("/device_status")
async def get_device_status():
    """Get current status of all devices"""
    return {
        "devices": device_status,
        "timestamp": datetime.now().isoformat(),
        "active_clients": len(active_clients)
    }

@app.get("/device_data")
async def get_device_data():
    """Get current data from all devices"""
    return {
        "devices": device_data,
        "timestamp": datetime.now().isoformat()
    }

# --- Run ---
def main():
    import uvicorn
    signal.signal(signal.SIGINT, signal_handler)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")

if __name__ == "__main__":
    main()
