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
# import paho.mqtt.client as mqtt  # Uncomment if using MQTT

# --- Pydantic Models ---

class Project(BaseModel):
    project_id: int
    project_name: str
    project_description: Optional[str]
    project_params: Optional[Dict]
    project_controls: Optional[Dict]
    created_at: datetime
    modified_at: Optional[datetime]

    class Config:
        from_attributes = True

class CommandRequest(BaseModel):
    device: str
    command: dict

class RunEndRequest(BaseModel):
    status: str = None
    notes: str = None

class RunCreateRequest(BaseModel):
    time_start: datetime | None = None
    time_end: datetime | None = None
    status: str | None = None
    notes: str | None = None

class ProjectCreate(BaseModel):
    project_name: str
    project_description: Optional[str]
    project_params: Optional[dict]
    project_controls: Optional[dict]

class ExperimentCreate(BaseModel):
    project_id: int
    experiment_name: str
    experiment_description: Optional[str]
    experiment_params: Optional[dict]

class RunCreate(BaseModel):
    project_id: int
    experiment_id: int
    run_name: str
    run_description: Optional[str]
    run_params: Optional[dict]
    run_status: str
    start_time: Optional[datetime] = None
    stop_time: Optional[datetime] = None

class RunVideoCreate(BaseModel):
    run_id: int
    video_path: str

class ExperimentCommandCreate(BaseModel):
    experiment_id: int
    device: str
    command_data: dict
    sequence_order: int

class ExperimentCommand(BaseModel):
    command_id: int
    experiment_id: int
    device: str
    command_data: dict
    sequence_order: int
    command_created_at: datetime

    class Config:
        from_attributes = True

# --- FastAPI Setup ---

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://mcu.local:3001",
    "http://10.147.18.184:3001",
    "http://192.168.2.1:3001",
    "http://102.168.2.10:3001",
    "*"  # Allow all for testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# --- Database ---

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/data_mgmt"
db_pool = None

def get_conn():
    return psycopg2.connect(host="localhost", database="data_mgmt", user="postgres", password="postgres")

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
        print("⚠️ Client disconnected")
    finally:
        active_clients.remove(websocket)
        await db_pool.release(db)

# --- MQTT (Optional: Commented out) ---

# MQTT_BROKER = "localhost"
# MQTT_PORT = 1883
# mqtt_client = mqtt.Client()
# def on_mqtt_message(client, userdata, message):
#     pass
# mqtt_client.on_message = on_mqtt_message
# mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
# mqtt_client.loop_start()

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

    # mqtt_client.publish(f"{payload.device}/cmd", json.dumps(command_with_ids))
    return {"success": True, "message": f"Command sent to {payload.device}"}

# --- Projects ---

@app.post("/projects")
def create_project(data: ProjectCreate):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO projects (project_name, project_description, project_params, project_controls)
        VALUES (%s, %s, %s, %s) RETURNING project_id;
    """, (data.project_name, data.project_description, json.dumps(data.project_params), json.dumps(data.project_controls)))
    conn.commit()
    return {"project_id": cur.fetchone()[0]}

@app.get("/projects/{project_id}", response_model=Project)
def get_project(project_id: int):
    conn = get_conn()
    # Use DictCursor to get results as dictionaries
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT 
            project_id,
            project_name,
            project_description,
            project_params,
            project_controls,
            created_at,
            modified_at
        FROM projects 
        WHERE project_id = %s;
    """, (project_id,))
    project = cur.fetchone()
    
    if not project:
        raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")
    
    cur.close()
    conn.close()
    return project

@app.get("/projects", response_model=List[Project])
def get_projects():
    conn = get_conn()
    # Use DictCursor to get results as dictionaries
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT 
            project_id,
            project_name,
            project_description,
            project_params,
            project_controls,
            created_at,
            modified_at
        FROM projects 
        ORDER BY created_at DESC;
    """)
    projects = cur.fetchall()
    
    cur.close()
    conn.close()
    return projects

@app.put("/projects/{project_id}")
def update_project(project_id: int, data: ProjectCreate):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        UPDATE projects 
        SET project_name = %s,
            project_description = %s,
            project_params = %s,
            project_controls = %s,
            modified_at = CURRENT_TIMESTAMP
        WHERE project_id = %s;
    """, (
        data.project_name,
        data.project_description,
        json.dumps(data.project_params),
        json.dumps(data.project_controls),
        project_id
    ))
    conn.commit()
    return {"message": f"Project {project_id} updated."}

@app.delete("/projects/{project_id}")
def delete_project(project_id: int):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM projects WHERE project_id = %s;", (project_id,))
    conn.commit()
    return {"message": f"Project {project_id} deleted."}

# --- Experiments ---

@app.post("/experiments")
def create_experiment(data: ExperimentCreate):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO experiments (project_id, experiment_name, experiment_description, experiment_params)
        VALUES (%s, %s, %s, %s) RETURNING experiment_id;
    """, (data.project_id, data.experiment_name, data.experiment_description, json.dumps(data.experiment_params)))
    conn.commit()
    return {"experiment_id": cur.fetchone()[0]}

@app.get("/projects/{project_id}/experiments")
def get_experiments(project_id: int):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT 
            experiment_id,
            project_id,
            experiment_name,
            experiment_description,
            experiment_params,
            run_count,
            created_at,
            modified_at
        FROM experiments 
        WHERE project_id = %s
        ORDER BY created_at DESC;
    """, (project_id,))
    experiments = cur.fetchall()
    cur.close()
    conn.close()
    return experiments

@app.get("/projects/{project_id}/experiments/{experiment_id}")
def get_experiment(project_id: int, experiment_id: int):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT 
            experiment_id,
            project_id,
            experiment_name,
            experiment_description,
            experiment_params,
            run_count,
            created_at,
            modified_at
        FROM experiments 
        WHERE project_id = %s AND experiment_id = %s;
    """, (project_id, experiment_id))
    experiment = cur.fetchone()
    
    if not experiment:
        raise HTTPException(status_code=404, detail=f"Experiment with ID {experiment_id} not found")
    
    cur.close()
    conn.close()
    return experiment

@app.put("/projects/{project_id}/experiments/{experiment_id}")
def update_experiment(project_id: int, experiment_id: int, data: ExperimentCreate):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        UPDATE experiments
        SET experiment_name = %s,
            experiment_description = %s,
            experiment_params = %s,
            modified_at = CURRENT_TIMESTAMP
        WHERE experiment_id = %s;
    """, (
        data.experiment_name,
        data.experiment_description,
        json.dumps(data.experiment_params),
        experiment_id
    ))
    conn.commit()
    return {"message": f"Experiment {experiment_id} updated."}

@app.delete("/projects/{project_id}/experiments/{experiment_id}")
def delete_experiment(project_id: int, experiment_id: int):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM experiments WHERE experiment_id = %s;", (experiment_id,))
    conn.commit()
    return {"message": f"Experiment {experiment_id} deleted."}

# --- Experiment Commands ---

@app.post("/experiments/{experiment_id}/commands")
def create_experiment_command(experiment_id: int, data: ExperimentCommandCreate):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        INSERT INTO experiment_commands (experiment_id, device, command_data, sequence_order)
        VALUES (%s, %s, %s, %s) RETURNING *;
    """, (experiment_id, data.device, json.dumps(data.command_data), data.sequence_order))
    command = cur.fetchone()
    conn.commit()
    return command

@app.get("/experiments/{experiment_id}/commands", response_model=List[ExperimentCommand])
def get_experiment_commands(experiment_id: int):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT * FROM experiment_commands 
        WHERE experiment_id = %s 
        ORDER BY sequence_order;
    """, (experiment_id,))
    commands = cur.fetchall()
    return commands

@app.delete("/experiments/{experiment_id}/commands/{command_id}")
def delete_experiment_command(experiment_id: int, command_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM experiment_commands 
        WHERE experiment_id = %s AND command_id = %s;
    """, (experiment_id, command_id))
    conn.commit()
    return {"message": f"Command {command_id} deleted from experiment {experiment_id}"}

@app.post("/experiments/{experiment_id}/commands/execute")
async def execute_experiment_commands(experiment_id: int):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT * FROM experiment_commands 
        WHERE experiment_id = %s 
        ORDER BY sequence_order;
    """, (experiment_id,))
    commands = cur.fetchall()
    
    for command in commands:
        command_with_ids = {
            **command['command_data'],
            "project_id": current_run_info["project_id"] or 0,
            "experiment_id": experiment_id,
            "run_id": current_run_info["run_id"] or 0
        }
        # mqtt_client.publish(f"{command['device']}/cmd", json.dumps(command_with_ids))
        await asyncio.sleep(0.1)  # Small delay between commands
    
    return {"success": True, "message": f"Executed {len(commands)} commands for experiment {experiment_id}"}

# --- Runs ---

@app.post("/projects/{project_id}/experiments/{experiment_id}/runs")
def create_run(project_id: int, experiment_id: int, data: RunCreate):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO runs (project_id, experiment_id, run_name, run_description, run_params, run_status, start_time, stop_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING run_id;
    """, (
        project_id,
        experiment_id,
        data.run_name,
        data.run_description,
        json.dumps(data.run_params),
        data.run_status,
        data.start_time,
        data.stop_time
    ))
    conn.commit()
    return {"run_id": cur.fetchone()[0]}

@app.get("/projects/{project_id}/experiments/{experiment_id}/runs")
def get_runs(project_id: int, experiment_id: int):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM runs WHERE experiment_id = %s ORDER BY created_at DESC;", (experiment_id,))
    return cur.fetchall()

@app.delete("/projects/{project_id}/experiments/{experiment_id}/runs/{run_id}")
def delete_run(project_id: int, experiment_id: int, run_id: int):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM runs WHERE run_id = %s;", (run_id,))
    conn.commit()
    return {"message": f"Run {run_id} deleted."}

@app.post("/projects/{project_id}/experiments/{experiment_id}/runs/{run_id}/stop")
async def stop_run(project_id: int, experiment_id: int, run_id: int, req: RunEndRequest, db=Depends(get_db)):
    stop_time = datetime.utcnow()
    status = req.status or "completed"
    notes = req.notes or ""

    update_query = """
        UPDATE runs
        SET stop_time = $1, run_status = $2, run_description = COALESCE(run_description, '') || $3
        WHERE run_id = $4
    """
    await db.execute(update_query, stop_time, status, f"\n[STOPPED @ {stop_time.isoformat()}] {notes}", run_id)
    await db_pool.release(db)

    if current_run_info["run_id"] == run_id:
        current_run_info["run_id"] = 0
        current_run_info["experiment_id"] = 0
        current_run_info["project_id"] = 0

    return {
        "message": f"✅ Run {run_id} stopped.",
        "stop_time": stop_time.isoformat(),
        "status": status
    }

# --- Run Videos ---

@app.post("/projects/{project_id}/experiments/{experiment_id}/runs/{run_id}/videos")
def create_video(project_id: int, experiment_id: int, run_id: int, data: RunVideoCreate):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("INSERT INTO run_videos (run_id, video_path) VALUES (%s, %s) RETURNING video_id;", (data.run_id, data.video_path))
    conn.commit()
    return {"video_id": cur.fetchone()[0]}

@app.get("/projects/{project_id}/experiments/{experiment_id}/runs/{run_id}/videos")
def get_videos(project_id: int, experiment_id: int, run_id: int):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM run_videos WHERE run_id = %s;", (run_id,))
    return cur.fetchall()

# --- Emergency Stop ---

@app.post("/projects/{project_id}/experiments/{experiment_id}/runs/{run_id}/emergency_stop")
async def emergency_stop(project_id: int, experiment_id: int, run_id: int, db=Depends(get_db)):
    emergency_command = {
        "mode": 0,
        "speed": 0,
        "position": 0,
        "current": 0,
        "load": 0
    }

    for device in expected_devices:
        # mqtt_client.publish(f"{device}/cmd", json.dumps(emergency_command))
        pass

    if current_run_info["run_id"]:
        run_id = current_run_info["run_id"]
        stop_time = datetime.utcnow()

        update_query = """
            UPDATE runs 
            SET stop_time = $1,
                run_status = 'aborted',
                run_description = COALESCE(run_description, '') || $2
            WHERE run_id = $3;
        """
        emergency_note = f"\n[EMERGENCY STOP at {stop_time.isoformat()}]"

        await db.execute(update_query, stop_time, emergency_note, run_id)
        await db_pool.release(db)

        current_run_info["run_id"] = 0
        current_run_info["experiment_id"] = 0
        current_run_info["project_id"] = 0

        return {
            "message": "🚨 Emergency stop triggered. Run aborted.",
            "run_id": run_id,
            "stop_time": stop_time.isoformat(),
            "status": "aborted"
        }

    return {
        "message": "🚨 Emergency stop triggered. No active run to abort."
    }

# --- Startup & Shutdown ---

@app.on_event("startup")
async def startup():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)

@app.on_event("shutdown")
async def shutdown():
    await db_pool.close()

def signal_handler(sig, frame):
    print("\n🔴 Keyboard Interrupt detected! Shutting down gracefully...")
    # mqtt_client.loop_stop()
    # mqtt_client.disconnect()

def main():
    import uvicorn
    signal.signal(signal.SIGINT, signal_handler)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")

if __name__ == "__main__":
    main()
