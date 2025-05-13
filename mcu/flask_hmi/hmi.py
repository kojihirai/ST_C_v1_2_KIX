from flask import Flask, render_template, request, jsonify
import json
import paho.mqtt.client as mqtt

app = Flask(__name__)

BROKER_IP = "192.168.2.1"
TOPIC = "lcu/cmd"

def send_mqtt_command(mode, direction=None, target=0):
    command = {
        "mode": mode,
        "direction": direction if direction is not None else 1,
        "target": target,
        "project_id": 1,
        "experiment_id": 1,
        "run_id": 1
    }
    
    client = mqtt.Client()
    client.connect(BROKER_IP, 1883, 60)
    client.publish(TOPIC, json.dumps(command))
    client.disconnect()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/reset', methods=['POST'])
def reset():
    send_mqtt_command(mode=8)
    return jsonify({"status": "success"})

@app.route('/stop', methods=['POST'])
def stop():
    send_mqtt_command(mode=0)
    return jsonify({"status": "success"})

@app.route('/forward', methods=['POST'])
def forward():
    target = request.json.get('target', 50)
    send_mqtt_command(mode=2, direction=1, target=target)
    return jsonify({"status": "success"})

@app.route('/backward', methods=['POST'])
def backward():
    target = request.json.get('target', 50)
    send_mqtt_command(mode=3, direction=2, target=target)
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
