from flask import Flask, render_template, jsonify, request
import requests
import json
from datetime import datetime

app = Flask(__name__)

# Configuration
BACKEND_URL = "http://localhost:8000"  # FastAPI backend URL

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/control')
def control():
    return render_template('control.html')

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

@app.route('/api/emergency_stop', methods=['POST'])
def emergency_stop():
    try:
        # Get current run info from backend
        response = requests.get(f"{BACKEND_URL}/current_run")
        current_run = response.json()
        
        if current_run.get('run_id'):
            # Call emergency stop endpoint
            response = requests.post(
                f"{BACKEND_URL}/projects/{current_run['project_id']}/experiments/{current_run['experiment_id']}/runs/{current_run['run_id']}/emergency_stop"
            )
            return jsonify(response.json())
        else:
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
    app.run(host='0.0.0.0', port=5000, debug=True)
