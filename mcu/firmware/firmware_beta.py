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
expected_devices = ["lcu", "dcu"]
active_clients = []

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
        payload = json.loads(message.payload.decode())
        device = message.topic.split('/')[0]
        if device in expected_devices:
            device_data[device] = payload
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

mqtt_client.on_message = on_mqtt_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
mqtt_client.loop_start()

# --- WebSocket ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db=Depends(get_db)):
    await websocket.accept()
    active_clients.append(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            print(f"Received: {message}")
            await websocket.send_text(f"Server Response: {message}")
    except WebSocketDisconnect:
        print("\u26a0\ufe0f Client disconnected")
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
        print(f"\U0001f3a5 Starting video recording for run {run_id}")
        video_recorder.start(run_id)

    elif prev_mode != 0 and new_mode == 0:
        print(f"\U0001f6d1 Stopping video recording for run {run_id}")
        video_path = video_recorder.stop()
        if video_path:
            print(f"\u2705 Video saved to {video_path}")

    mqtt_client.publish(f"{device}/cmd", json.dumps(command_with_ids))
    return {"success": True, "message": f"Command sent to {device}"}

# --- Startup/Shutdown ---
@app.on_event("startup")
async def startup():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)

@app.on_event("shutdown")
async def shutdown():
    await db_pool.close()
    if video_recorder.running:
        print("\U0001f504 Graceful shutdown: stopping video...")
        video_recorder.stop()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

# --- Signal Handling ---
def signal_handler(sig, frame):
    print("\nKeyboard Interrupt detected! Shutting down gracefully...")
    asyncio.get_event_loop().create_task(shutdown())

# --- Run ---
def main():
    import uvicorn
    signal.signal(signal.SIGINT, signal_handler)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")

if __name__ == "__main__":
    main()
