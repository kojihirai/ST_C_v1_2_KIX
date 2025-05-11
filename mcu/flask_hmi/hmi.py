from flask import Flask, render_template, jsonify, request, redirect, url_for
import requests
import json
from datetime import datetime

app = Flask(__name__)

# Configuration
# BACKEND_URL = "http://localhost:8000"  # FastAPI backend URL
BACKEND_URL = "http://10.147.18.184:8000"  # FastAPI backend URL
# Global state
system_status = "stopped"
mode = "manual"  # manual, experiment, program
selected_project_id = None
selected_experiment_id = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/control')
def control():
    return render_template('control.html')

@app.route('/projects')
def projects():
    try:
        response = requests.get(f"{BACKEND_URL}/projects")
        projects = response.json()
        return render_template('projects.html', projects=projects)
    except Exception as e:
        return render_template('projects.html', projects=[], error=str(e))

@app.route('/api/system_status')
def get_system_status():
    return jsonify({
        "status": system_status,
        "mode": mode,
        "selected_project_id": selected_project_id,
        "selected_experiment_id": selected_experiment_id
    })

@app.route('/api/projects')
def get_projects():
    try:
        response = requests.get(f"{BACKEND_URL}/projects")
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<int:project_id>/experiments')
def get_experiments(project_id):
    try:
        response = requests.get(f"{BACKEND_URL}/projects/{project_id}/experiments")
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/send_command', methods=['POST'])
def send_command():
    try:
        data = request.json
        device = data.get('device')
        command = data.get('command')
        
        if not device or not command:
            return jsonify({'error': 'Missing device or command'}), 400
            
        # Forward command to FastAPI backend
        response = requests.post(
            f"{BACKEND_URL}/send_command/",
            json={'device': device, 'command': command}
        )
        
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/start_manual', methods=['POST'])
def start_manual():
    global system_status
    system_status = "running"
    return jsonify({"status": "success", "message": "Manual mode started"})

@app.route('/api/stop_manual', methods=['POST'])
def stop_manual():
    global system_status
    system_status = "stopped"
    return jsonify({"status": "success", "message": "Manual mode stopped"})

@app.route('/api/start_experiment', methods=['POST'])
def start_experiment():
    global system_status
    try:
        data = request.json
        project_id = data.get('project_id')
        experiment_id = data.get('experiment_id')
        
        if not project_id or not experiment_id:
            return jsonify({'error': 'Missing project_id or experiment_id'}), 400
            
        # Start experiment in backend
        response = requests.post(
            f"{BACKEND_URL}/projects/{project_id}/experiments/{experiment_id}/start"
        )
        
        system_status = "running"
        return jsonify({"status": "success", "message": "Experiment started"})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop_experiment', methods=['POST'])
def stop_experiment():
    global system_status
    try:
        data = request.json
        project_id = data.get('project_id')
        experiment_id = data.get('experiment_id')
        
        if not project_id or not experiment_id:
            return jsonify({'error': 'Missing project_id or experiment_id'}), 400
            
        # Stop experiment in backend
        response = requests.post(
            f"{BACKEND_URL}/projects/{project_id}/experiments/{experiment_id}/stop"
        )
        
        system_status = "stopped"
        return jsonify({"status": "success", "message": "Experiment stopped"})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/set_mode', methods=['POST'])
def set_mode():
    global mode
    try:
        data = request.json
        new_mode = data.get('mode')
        
        if new_mode not in ['manual', 'experiment', 'program']:
            return jsonify({'error': 'Invalid mode'}), 400
            
        mode = new_mode
        return jsonify({"status": "success", "message": f"Mode set to {new_mode}"})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/set_project', methods=['POST'])
def set_project():
    global selected_project_id
    try:
        data = request.json
        project_id = data.get('project_id')
        
        if project_id is None:
            return jsonify({'error': 'Missing project_id'}), 400
            
        selected_project_id = project_id
        return jsonify({"status": "success", "message": f"Project {project_id} selected"})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/set_experiment', methods=['POST'])
def set_experiment():
    global selected_experiment_id
    try:
        data = request.json
        experiment_id = data.get('experiment_id')
        
        if experiment_id is None:
            return jsonify({'error': 'Missing experiment_id'}), 400
            
        selected_experiment_id = experiment_id
        return jsonify({"status": "success", "message": f"Experiment {experiment_id} selected"})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emergency_stop', methods=['POST'])
def emergency_stop():
    global system_status
    try:
        # Get current run info from backend
        response = requests.get(f"{BACKEND_URL}/current_run")
        current_run = response.json()
        
        if current_run.get('run_id'):
            # Call emergency stop endpoint
            response = requests.post(
                f"{BACKEND_URL}/projects/{current_run['project_id']}/experiments/{current_run['experiment_id']}/runs/{current_run['run_id']}/emergency_stop"
            )
            system_status = "stopped"
            return jsonify(response.json())
        else:
            system_status = "stopped"
            return jsonify({'message': 'No active run to stop'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset', methods=['POST'])
def reset():
    try:
        # Get current run info from backend
        response = requests.get(f"{BACKEND_URL}/current_run")
        current_run = response.json()
        
        if current_run.get('project_id') and current_run.get('experiment_id'):
            # Call reset endpoint
            response = requests.post(
                f"{BACKEND_URL}/projects/{current_run['project_id']}/experiments/{current_run['experiment_id']}/reset"
            )
            return jsonify(response.json())
        else:
            return jsonify({'message': 'No active experiment to reset'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5032, debug=True)
