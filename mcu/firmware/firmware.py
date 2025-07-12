from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import json
import asyncio
import signal
import paho.mqtt.client as mqtt
import time
import cv2
import shutil
import os
import threading

# --- Models ---

class CommandRequest(BaseModel):
    device: str
    command: dict

class DeviceStatus(BaseModel):
    device: str
    status: str  # "online", "offline", "warning"
    last_seen: Optional[datetime]
    data_count: int

# --- App Setup ---

app = FastAPI()

origins = ["*"]  # Allow all origins during development

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
device_status = {}
monitoring_task = None

# --- Video Recording State ---

recording_thread = None
recording_flag = threading.Event()
last_mode = 0
last_dir = 0

USB_MOUNT_PATH = "/media/pi/BEA6-BBCE5"
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 20.0

# --- Device Monitoring ---

def initialize_device_status():
    for device in expected_devices:
        device_status[device] = DeviceStatus(
            device=device,
            status="offline",
            last_seen=None,
            data_count=0
        )

def update_device_status(device: str, data: dict):
    global last_mode, last_dir, recording_thread

    if device not in device_status:
        return

    current_time = datetime.now()
    device_status[device].last_seen = current_time
    device_status[device].data_count += 1

    previous_status = device_status[device].status
    device_status[device].status = "online"
    if previous_status != "online":
        asyncio.create_task(broadcast_device_status())

    # Handle recording trigger
    mode = data.get("mode", 0)
    direction = data.get("dir", 0)

    if (last_mode == 0 and mode != 0) or (last_dir == 0 and direction != 0):
        if not recording_flag.is_set():
            recording_flag.set()
            recording_thread = threading.Thread(target=record_video_to_usb)
            recording_thread.start()
    elif (last_mode != 0 and mode == 0) and (last_dir != 0 and direction == 0):
        if recording_flag.is_set():
            recording_flag.clear()
            if recording_thread and recording_thread.is_alive():
                recording_thread.join()

    last_mode = mode
    last_dir = direction

def check_device_health():
    current_time = datetime.now()
    for device in expected_devices:
        status = device_status.get(device)
        if not status or not status.last_seen:
            continue
        time_since = (current_time - status.last_seen).total_seconds()
        if time_since > 60:
            if status.status != "offline":
                status.status = "offline"
                asyncio.create_task(broadcast_device_status())
        elif time_since > 45:
            if status.status != "warning":
                status.status = "warning"
                asyncio.create_task(broadcast_device_status())

async def monitoring_loop():
    while True:
        try:
            check_device_health()
            await broadcast_device_status()
            await asyncio.sleep(5)
        except Exception as e:
            print(f"[monitor] Error: {e}")
            await asyncio.sleep(5)

# --- Video Recording ---

def record_video_to_usb():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"video_{timestamp}.avi"
    save_path = os.path.join(USB_MOUNT_PATH, filename)

    if not os.path.exists(USB_MOUNT_PATH):
        print(f"[Recorder] USB drive not found: {USB_MOUNT_PATH}")
        return

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    if not cap.isOpened():
        print("[Recorder] Failed to open webcam.")
        return

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(save_path, fourcc, FPS, (FRAME_WIDTH, FRAME_HEIGHT))
    print(f"[Recorder] Recording started: {save_path}")

    while recording_flag.is_set():
        ret, frame = cap.read()
        if not ret:
            print("[Recorder] Frame grab failed.")
            break

        total, used, free = shutil.disk_usage(USB_MOUNT_PATH)
        if free < 50 * 1024 * 1024:
            print("[Recorder] USB full. Stopping.")
            break

        out.write(frame)
        time.sleep(1 / FPS)

    cap.release()
    out.release()
    print("[Recorder] Recording stopped.")

# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await websocket.accept()
        active_clients.append(websocket)
        await websocket.send_text(json.dumps({
            "type": "device_status_update",
            "data": {
                "devices": [s.dict() for s in device_status.values()],
                "timestamp": datetime.now().isoformat()
            }
        }))
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
                if data.get("type") == "request_status":
                    await websocket.send_text(json.dumps({
                        "type": "device_status_update",
                        "data": {
                            "devices": [s.dict() for s in device_status.values()],
                            "timestamp": datetime.now().isoformat()
                        }
                    }))
            except:
                await websocket.send_text(f"Echo: {msg}")
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in active_clients:
            active_clients.remove(websocket)

async def broadcast_device_status():
    if not active_clients:
        return
    message = json.dumps({
        "type": "device_status_update",
        "data": {
            "devices": [s.dict() for s in device_status.values()],
            "timestamp": datetime.now().isoformat()
        }
    })
    for client in active_clients:
        try:
            await client.send_text(message)
        except:
            active_clients.remove(client)

# --- MQTT ---

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
mqtt_client = mqtt.Client()

def on_mqtt_message(client, userdata, message):
    try:
        payload = json.loads(message.payload.decode())
        topic = message.topic
        device = topic.split("/")[0]
        if device in expected_devices:
            device_data[device] = payload
            update_device_status(device, payload)
    except Exception as e:
        print(f"[MQTT] Message error: {e}")

def on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT] Connected.")
        for dev in expected_devices:
            client.subscribe(f"{dev}/#")
    else:
        print(f"[MQTT] Failed with code {rc}")

mqtt_client.on_message = on_mqtt_message
mqtt_client.on_connect = on_mqtt_connect
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
mqtt_client.loop_start()

# --- REST Endpoints ---

@app.post("/send_command/")
async def send_command(payload: CommandRequest):
    if payload.device not in expected_devices:
        return {"success": False, "message": "Invalid device"}
    mqtt_client.publish(f"{payload.device}/cmd", json.dumps(payload.command))
    return {"success": True}

@app.get("/device_status/")
async def get_device_status():
    return {
        "devices": [s.dict() for s in device_status.values()],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/device_data/")
async def get_all_device_data():
    return {
        "devices": device_data,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/device_data/{device}")
async def get_device_data(device: str):
    if device not in device_data:
        raise HTTPException(status_code=404, detail="No data")
    return {
        "device": device,
        "data": device_data[device],
        "timestamp": datetime.now().isoformat()
    }

# --- Startup / Shutdown ---

@app.on_event("startup")
async def startup():
    global monitoring_task
    initialize_device_status()
    monitoring_task = asyncio.create_task(monitoring_loop())

@app.on_event("shutdown")
async def shutdown():
    global monitoring_task
    if monitoring_task:
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

# --- Entrypoint ---

def signal_handler(sig, frame):
    print("Interrupt received. Shutting down...")
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    exit(0)

def main():
    import uvicorn
    signal.signal(signal.SIGINT, signal_handler)
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
