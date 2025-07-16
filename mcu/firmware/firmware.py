from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
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
import glob

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

USB_MOUNT_PATH = "/media/pi/BEA6-BBCE6"
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

# --- Video Endpoints ---

@app.get("/videos/")
async def list_videos():
    """List all available video files on USB drive"""
    if not os.path.exists(USB_MOUNT_PATH):
        raise HTTPException(status_code=404, detail="USB drive not found")
    
    video_files = glob.glob(os.path.join(USB_MOUNT_PATH, "*.avi"))
    videos = []
    
    for video_file in video_files:
        filename = os.path.basename(video_file)
        stat = os.stat(video_file)
        videos.append({
            "filename": filename,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })
    
    return {
        "videos": sorted(videos, key=lambda x: x["modified"], reverse=True),
        "total_count": len(videos)
    }

@app.get("/videos/{filename}")
async def stream_video(filename: str):
    """Stream a specific video file"""
    if not os.path.exists(USB_MOUNT_PATH):
        raise HTTPException(status_code=404, detail="USB drive not found")
    
    video_path = os.path.join(USB_MOUNT_PATH, filename)
    
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    # Validate filename to prevent directory traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    return FileResponse(
        path=video_path,
        media_type="video/x-msvideo",
        filename=filename
    )

@app.get("/stream/{filename}")
async def stream_video_with_ranges(filename: str, range: Optional[str] = None):
    """Stream video with proper range support for browser video players"""
    if not os.path.exists(USB_MOUNT_PATH):
        raise HTTPException(status_code=404, detail="USB drive not found")
    
    video_path = os.path.join(USB_MOUNT_PATH, filename)
    
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    # Validate filename to prevent directory traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    file_size = os.path.getsize(video_path)
    
    if range:
        # Parse range header (e.g., "bytes=0-1023")
        try:
            range_header = range.replace("bytes=", "").split("-")
            start = int(range_header[0]) if range_header[0] else 0
            end = int(range_header[1]) if range_header[1] else file_size - 1
            
            if start >= file_size:
                raise HTTPException(status_code=416, detail="Range not satisfiable")
            
            end = min(end, file_size - 1)
            content_length = end - start + 1
            
            def video_stream():
                with open(video_path, "rb") as f:
                    f.seek(start)
                    remaining = content_length
                    chunk_size = 8192
                    while remaining > 0:
                        chunk = f.read(min(chunk_size, remaining))
                        if not chunk:
                            break
                        yield chunk
                        remaining -= len(chunk)
            
            return StreamingResponse(
                video_stream(),
                media_type="video/x-msvideo",
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(content_length)
                }
            )
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="Invalid range header")
    else:
        # Full file response
        def video_stream():
            with open(video_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk
        
        return StreamingResponse(
            video_stream(),
            media_type="video/x-msvideo",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size)
            }
        )

@app.get("/videos/{filename}/info")
async def get_video_info(filename: str):
    """Get information about a specific video file"""
    if not os.path.exists(USB_MOUNT_PATH):
        raise HTTPException(status_code=404, detail="USB drive not found")
    
    video_path = os.path.join(USB_MOUNT_PATH, filename)
    
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    # Validate filename to prevent directory traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    stat = os.stat(video_path)
    
    # Try to get video metadata using OpenCV
    cap = cv2.VideoCapture(video_path)
    if cap.isOpened():
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0
        cap.release()
    else:
        fps = 0
        frame_count = 0
        width = 0
        height = 0
        duration = 0
    
    return {
        "filename": filename,
        "size": stat.st_size,
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "video_info": {
            "fps": fps,
            "frame_count": frame_count,
            "width": width,
            "height": height,
            "duration_seconds": duration
        }
    }

@app.delete("/videos/{filename}")
async def delete_video(filename: str):
    """Delete a specific video file"""
    if not os.path.exists(USB_MOUNT_PATH):
        raise HTTPException(status_code=404, detail="USB drive not found")
    
    video_path = os.path.join(USB_MOUNT_PATH, filename)
    
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    # Validate filename to prevent directory traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    try:
        os.remove(video_path)
        return {"success": True, "message": f"Video {filename} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete video: {str(e)}")

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
