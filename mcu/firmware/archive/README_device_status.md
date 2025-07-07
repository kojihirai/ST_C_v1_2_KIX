# Device Status Monitoring System

## Overview

The firmware has been updated to include comprehensive device status monitoring that tracks the health and connectivity of all expected devices (LCU, DCU, SDU) via MQTT and displays real-time status indicators on the HMI frontend.

## Features

### Backend (Firmware)
- **MQTT Endpoint Monitoring**: Listens to `{device}/data` and `{device}/error` topics for all expected devices
- **Real-time Status Tracking**: Maintains device status with timestamps and error information
- **Automatic Disconnection Detection**: Marks devices as disconnected if no data received for >10 seconds
- **WebSocket Status Broadcasting**: Sends status updates to all connected HMI clients
- **Background Monitoring**: Periodic status checks every 5 seconds

### Frontend (HMI)
- **Status Indicator Bar**: Fixed bottom bar showing device status with color coding
- **Real-time Updates**: Live status updates via WebSocket
- **Visual Indicators**: 
  - 🟢 Green: Device connected and sending data
  - 🔴 Red: Device error
  - ⚫ Gray: Device disconnected
- **Hover Tooltips**: Show last seen time and error details
- **Responsive Design**: Works on different screen sizes

## Device Status States

1. **Connected**: Device is actively sending data
2. **Error**: Device has reported an error
3. **Disconnected**: No data received for >10 seconds

## MQTT Topics

The system monitors these MQTT topics:
- `lcu/data` - LCU device data
- `lcu/error` - LCU error messages
- `dcu/data` - DCU device data  
- `dcu/error` - DCU error messages
- `sdu/data` - SDU device data
- `sdu/error` - SDU error messages

## API Endpoints

### GET `/device_status`
Returns current status of all devices:
```json
{
  "devices": {
    "lcu": {
      "status": "connected",
      "last_seen": "2024-01-15T10:30:00",
      "error": null
    },
    "dcu": {
      "status": "error", 
      "last_seen": "2024-01-15T10:29:55",
      "error": "Communication timeout"
    },
    "sdu": {
      "status": "disconnected",
      "last_seen": null,
      "error": "No data received recently"
    }
  },
  "timestamp": "2024-01-15T10:30:00",
  "active_clients": 2
}
```

### GET `/device_data`
Returns current data from all devices.

## WebSocket Messages

The system sends device status updates via WebSocket with this format:
```json
{
  "type": "device_status",
  "data": {
    "devices": { /* device status object */ },
    "timestamp": "2024-01-15T10:30:00"
  }
}
```

## Testing

Use the provided test script to simulate device messages:

```bash
cd v1_2_KIX/mcu/firmware
python test_mqtt.py
```

This will send simulated data and error messages from all devices to test the monitoring system.

## Configuration

### Timeout Settings
- **Data timeout**: 10 seconds (devices marked as disconnected after this time)
- **Status check interval**: 5 seconds (background monitoring frequency)

### Expected Devices
Currently configured for: `["lcu", "dcu", "sdu"]`

## Troubleshooting

### Device Shows as Disconnected
1. Check MQTT broker is running: `systemctl status mosquitto`
2. Verify device is publishing to correct topics
3. Check network connectivity between device and MCU
4. Review MQTT logs for connection issues

### Status Not Updating on HMI
1. Check WebSocket connection in browser dev tools
2. Verify firmware is running and accessible
3. Check browser console for JavaScript errors
4. Ensure CORS is properly configured

### Error Messages
- Check device logs for error details
- Verify device firmware is functioning correctly
- Review MQTT message format matches expected schema

## Future Enhancements

- Device heartbeat/ping mechanism
- Configurable timeout values
- Device-specific status indicators
- Historical status logging
- Alert notifications for critical errors 