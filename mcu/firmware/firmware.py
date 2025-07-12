from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import json
import asyncio
import signal
import paho.mqtt.client as mqtt
import time
import cv2
import os
import threading

# === CAMERA RECORDING CONFIGURATION ===
USB_MOUNT_PATH = "/media/pi/BEA6-BBCE5"  # USB drive mount point
CAMERA_FPS = 20.0
CAMERA_RESOLUTION = (640, 480)
CAMERA_CODEC = 'XVID'  # .avi format

class VideoRecorder:
    """Thread-safe video recorder for camera recording"""
    def __init__(self, save_dir=USB_MOUNT_PATH, fps=CAMERA_FPS, resolution=CAMERA_RESOLUTION):
        self.save_dir = save_dir
        self.fps = fps
        self.resolution = resolution
        self.out = None
        self.cap = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.filename = None
        self.recording_start_time = None

    def _record(self, filename):
        """Internal recording function that runs in a separate thread"""
        try:
            self.cap = cv2.VideoCapture(0)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            
            if not self.cap.isOpened():
                print("Failed to open camera")
                return
                
            fourcc = cv2.VideoWriter_fourcc(*CAMERA_CODEC)
            self.out = cv2.VideoWriter(filename, fourcc, self.fps, self.resolution)
            
            print(f"Started recording to {filename}")
            
            while self.running and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    self.out.write(frame)
                else:
                    print("Failed to grab frame")
                    break
                    
        except Exception as e:
            print(f"Error during recording: {e}")
        finally:
            self._cleanup()

    def _cleanup(self):
        """Clean up camera and video writer resources"""
        if self.out:
            self.out.release()
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()

    def start(self, device_name="unknown"):
        """Start recording video"""
        with self.lock:
            if self.running:
                print("Recording already in progress")
                return False
                
            # Check if USB drive is mounted
            if not os.path.exists(self.save_dir):
                print(f"USB drive not found at {self.save_dir}")
                return False
                
            # Create filename with timestamp and device info
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.filename = os.path.join(self.save_dir, f"recording_{device_name}_{timestamp}.avi")
            self.recording_start_time = datetime.now()
            
            self.running = True
            self.thread = threading.Thread(target=self._record, args=(self.filename,), daemon=True)
            self.thread.start()
            print(f"Started recording for device {device_name}")
            return True

    def stop(self):
        """Stop recording and return the filename"""
        with self.lock:
            if not self.running:
                return None
                
            self.running = False
            
            # Wait for recording thread to finish
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=2.0)
                
            filename = self.filename
            duration = None
            if self.recording_start_time:
                duration = (datetime.now() - self.recording_start_time).total_seconds()
                
            print(f"Stopped recording. Duration: {duration:.1f}s, File: {filename}")
            return filename

    def is_recording(self):
        """Check if currently recording"""
        with self.lock:
            return self.running

# Initialize video recorder
video_recorder = VideoRecorder()

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
    "http://10.147.18.68:3000",
    "http://10.147.18.68:3001",
    "http://192.168.2.1:3001",
    "http://102.168.2.10:3001",
    "*"  # Allow all origins for development
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
    try:
        await websocket.accept()
        print("WebSocket client connected")
        active_clients.append(websocket)
        
        # Send initial device status
        try:
            initial_status = {
                "type": "device_status_update",
                "data": {
                    "devices": [status.dict() for status in device_status.values()],
                    "timestamp": datetime.now().isoformat()
                }
            }
            await websocket.send_text(json.dumps(initial_status))
            print("Initial status sent to client")
        except Exception as e:
            print(f"Error sending initial status: {e}")
        
        while True:
            try:
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
                break
            except Exception as e:
                print(f"Error handling message: {e}")
                break
                
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if websocket in active_clients:
            active_clients.remove(websocket)
        print("WebSocket client removed from active clients")

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

    # Get current device data to check for mode/dir changes
    current_data = device_data.get(payload.device, {})
    current_mode = current_data.get("mode", 0)
    current_dir = current_data.get("direction", 0)
    
    # Get new mode and direction from command
    new_mode = payload.command.get("mode", current_mode)
    new_dir = payload.command.get("direction", current_dir)
    
    # Check for mode/dir changes that should trigger camera recording
    mode_changed = new_mode != current_mode
    dir_changed = new_dir != current_dir
    
    # Start recording: when mode or dir changes from 0 to non-0
    should_start_recording = (
        (mode_changed and current_mode == 0 and new_mode != 0) or
        (dir_changed and current_dir == 0 and new_dir != 0)
    )
    
    # Stop recording: when mode or dir changes from non-0 to 0
    should_stop_recording = (
        (mode_changed and current_mode != 0 and new_mode == 0) or
        (dir_changed and current_dir != 0 and new_dir == 0)
    )
    
    # Handle camera recording
    recording_status = ""
    if should_start_recording and not video_recorder.is_recording():
        if video_recorder.start(payload.device):
            recording_status = f" - Started camera recording for {payload.device}"
        else:
            recording_status = f" - Failed to start camera recording for {payload.device}"
    elif should_stop_recording and video_recorder.is_recording():
        video_path = video_recorder.stop()
        if video_path:
            recording_status = f" - Stopped camera recording: {os.path.basename(video_path)}"
        else:
            recording_status = f" - Stopped camera recording for {payload.device}"
    
    # Log the changes
    if mode_changed or dir_changed:
        print(f"Device {payload.device}: mode {current_mode}->{new_mode}, dir {current_dir}->{new_dir}{recording_status}")

    command_with_ids = {
        **payload.command,
    }   

    mqtt_client.publish(f"{payload.device}/cmd", json.dumps(command_with_ids))
    return {"success": True, "message": f"Command sent to {payload.device}{recording_status}"}

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

@app.get("/device_data/{device}")
async def get_device_data(device: str):
    """Get the latest data for a specific device"""
    if device not in expected_devices:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device not in device_data:
        return {"error": "No data available for this device"}
    
    return {
        "device": device,
        "data": device_data[device],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/device_data/")
async def get_all_device_data():
    """Get the latest data for all devices"""
    return {
        "devices": device_data,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/camera_status/")
async def get_camera_status():
    """Get camera recording status"""
    return {
        "is_recording": video_recorder.is_recording(),
        "current_file": video_recorder.filename if video_recorder.is_recording() else None,
        "recording_start_time": video_recorder.recording_start_time.isoformat() if video_recorder.recording_start_time else None,
        "usb_mount_path": USB_MOUNT_PATH,
        "usb_available": os.path.exists(USB_MOUNT_PATH),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/camera/start/")
async def start_camera_recording(device: str = "manual"):
    """Manually start camera recording"""
    if video_recorder.is_recording():
        return {"success": False, "message": "Recording already in progress"}
    
    if video_recorder.start(device):
        return {"success": True, "message": f"Started recording for {device}"}
    else:
        return {"success": False, "message": "Failed to start recording"}

@app.post("/camera/stop/")
async def stop_camera_recording():
    """Manually stop camera recording"""
    if not video_recorder.is_recording():
        return {"success": False, "message": "No recording in progress"}
    
    video_path = video_recorder.stop()
    if video_path:
        return {"success": True, "message": f"Stopped recording: {os.path.basename(video_path)}"}
    else:
        return {"success": True, "message": "Stopped recording"}



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
