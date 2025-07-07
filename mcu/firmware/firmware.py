from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import asyncpg
import psycopg2
import psycopg2.extras
import json
import asyncio
import signal
import paho.mqtt.client as mqtt

class CommandRequest(BaseModel):
    device: str
    command: dict


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

current_run_info = {
    "run_id": 0,
    "experiment_id": 0,
    "project_id": 0
}

# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_clients.append(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            print(f"Received: {message}")
            await websocket.send_text(f"Server Response: {message}")
    except WebSocketDisconnect:
        print("⚠️ Client disconnected")
    finally:
        active_clients.remove(websocket)

# --- MQTT Setup ---

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
mqtt_client = mqtt.Client()

def on_mqtt_message(client, userdata, message):
    """Handle incoming MQTT messages"""
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

@app.post("/send_command/")
async def send_command(payload: CommandRequest):
    if payload.device not in expected_devices:
        return {"success": False, "message": "Invalid device"}

    command_with_ids = {
        **payload.command,
        "project_id": current_run_info["project_id"] or 0,
        "experiment_id": current_run_info["experiment_id"] or 0,
        "run_id": current_run_info["run_id"] or 0
    }

    mqtt_client.publish(f"{payload.device}/cmd", json.dumps(command_with_ids))
    return {"success": True, "message": f"Command sent to {payload.device}"}

# --- Startup & Shutdown ---

@app.on_event("startup")
async def startup():
        pass

@app.on_event("shutdown")
async def shutdown(): pass

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
