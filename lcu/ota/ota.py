from flask import Flask, render_template, request, jsonify
import os
import shutil
import subprocess
import json
from datetime import datetime
import glob

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = '/home/pi/Desktop/lcu/firmware'
ARCHIVE_FOLDER = os.path.join(UPLOAD_FOLDER, 'archive')
MAX_ARCHIVE_VERSIONS = 3
PM2_APP_NAME = 'firmware'

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ARCHIVE_FOLDER, exist_ok=True)

def get_pm2_status():
    try:
        result = subprocess.run(['pm2', 'jlist'], capture_output=True, text=True)
        processes = json.loads(result.stdout)
        for process in processes:
            if process['name'] == PM2_APP_NAME:
                return {
                    'status': process['pm2_env']['status'],
                    'uptime': process['pm2_env']['pm_uptime'],
                    'memory': process['monit']['memory'],
                    'cpu': process['monit']['cpu']
                }
        return {'status': 'not_found'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def archive_current_firmware():
    current_firmware = os.path.join(UPLOAD_FOLDER, 'firmware.py')
    if os.path.exists(current_firmware):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_name = f'firmware_{timestamp}.py'
        shutil.move(current_firmware, os.path.join(ARCHIVE_FOLDER, archive_name))
        
        # Clean up old archives
        archives = glob.glob(os.path.join(ARCHIVE_FOLDER, 'firmware_*.py'))
        archives.sort(reverse=True)
        for old_archive in archives[MAX_ARCHIVE_VERSIONS:]:
            os.remove(old_archive)

@app.route('/')
def index():
    pm2_status = get_pm2_status()
    return render_template('index.html', pm2_status=pm2_status)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not file.filename.endswith('.py'):
        return jsonify({'error': 'Only Python files are allowed'}), 400

    try:
        # Archive current firmware
        archive_current_firmware()
        
        # Save new firmware
        file_path = os.path.join(UPLOAD_FOLDER, 'firmware.py')
        file.save(file_path)
        
        # Restart PM2 process
        subprocess.run(['pm2', 'restart', PM2_APP_NAME])
        
        return jsonify({'message': 'Firmware updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status')
def status():
    return jsonify(get_pm2_status())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1215)
