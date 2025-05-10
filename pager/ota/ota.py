from flask import Flask, render_template, request, jsonify
import os
import requests
import json
from datetime import datetime

app = Flask(__name__)

# PagerDuty API configuration
PAGERDUTY_API_TOKEN = 'fb7168b8f0c74f0ac0b7ca3daaf80e3f'
PAGERDUTY_API_URL = 'https://events.pagerduty.com/v2/enqueue'

def create_pagerduty_incident(title, description, urgency='high', priority='P1'):
    headers = {
        'Authorization': f'Token token={PAGERDUTY_API_TOKEN}',
        'Content-Type': 'application/json',
        'Accept': 'application/vnd.pagerduty+json;version=2'
    }
    
    payload = {
        'payload': {
            'summary': title,
            'severity': urgency,
            'source': 'OTA System',
            'custom_details': description
        },
        'routing_key': os.getenv('PAGERDUTY_ROUTING_KEY', PAGERDUTY_API_TOKEN),  # Use routing key or fallback to API token
        'event_action': 'trigger',
        'client': 'OTA System',
        'client_url': 'http://localhost:1215'
    }
    
    try:
        response = requests.post(PAGERDUTY_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error details: {e.response.text if hasattr(e, 'response') else str(e)}")
        return {'error': str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create-page', methods=['POST'])
def create_page():
    data = request.json
    
    if not all(key in data for key in ['title', 'description']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    result = create_pagerduty_incident(
        title=data['title'],
        description=data['description'],
        urgency=data.get('urgency', 'high'),
        priority=data.get('priority', 'P1')
    )
    
    if 'error' in result:
        return jsonify(result), 500
    
    return jsonify({'message': 'Page created successfully', 'incident': result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1215)
