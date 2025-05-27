from flask import Flask, render_template, request, jsonify
import os
import requests
import json
from datetime import datetime
import threading
import time

app = Flask(__name__)

PAGERDUTY_ROUTING_KEY = 'fb7168b8f0c74f0ac0b7ca3daaf80e3f'
PAGERDUTY_EVENTS_URL = 'https://events.pagerduty.com/v2/enqueue'

is_updating = False
status_check_thread = None

def send_pagerduty_alert(title, description, urgency='high', priority='P1'):
    if not PAGERDUTY_ROUTING_KEY:
        print("PagerDuty routing key missing. Skipping alert.")
        return

    headers = {
        'Content-Type': 'application/json'
    }

    severity_map = {
        'high': 'critical',
        'medium': 'warning',
        'low': 'info'
    }
    severity = severity_map.get(urgency.lower(), 'critical')

    payload = {
        'routing_key': PAGERDUTY_ROUTING_KEY,
        'event_action': 'trigger',
        'payload': {
            'summary': title,
            'severity': severity,
            'source': 'Pager OTA Service',
            'custom_details': {
                'description': description,
                'priority': priority,
                'urgency': urgency,
                'timestamp': datetime.now().isoformat()
            }
        }
    }

    try:
        print(f"Sending payload to PagerDuty: {json.dumps(payload, indent=2)}")
        response = requests.post(PAGERDUTY_EVENTS_URL, headers=headers, json=payload)
        
        if response.status_code != 202:
            error_msg = f"PagerDuty API error: {response.status_code}\nResponse: {response.text}"
            print(error_msg)
            return {'error': error_msg}
            
        print(f"PagerDuty alert sent successfully: {response.json()}")
        return response.json()
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to send PagerDuty alert: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            error_msg += f"\nResponse: {e.response.text}"
        print(error_msg)
        return {'error': error_msg}
    except Exception as e:
        error_msg = f"Unexpected error sending PagerDuty alert: {str(e)}"
        print(error_msg)
        return {'error': error_msg}

def background_status_check():
    while True:
        if not is_updating:
            pass
        time.sleep(60)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create-page', methods=['POST'])
def create_page():
    global is_updating
    data = request.json
    
    if not all(key in data for key in ['title', 'description']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        is_updating = True
        result = send_pagerduty_alert(
            title=data['title'],
            description=data['description'],
            urgency=data.get('urgency', 'high'),
            priority=data.get('priority', 'P1')
        )
        is_updating = False
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify({'message': 'Page created successfully', 'incident': result})
    except Exception as e:
        is_updating = False
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    status_check_thread = threading.Thread(target=background_status_check, daemon=True)
    status_check_thread.start()
    app.run(host='0.0.0.0', port=1215)
