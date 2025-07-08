#!/usr/bin/env python3
"""
Test script to check MCU server status and available endpoints
"""
import requests
import json

def test_server():
    base_url = "http://10.147.18.68:8000"
    
    print("Testing MCU Server Status")
    print("=" * 50)
    
    # Test 1: Basic connectivity
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"✓ Root endpoint (/) - Status: {response.status_code}")
        print(f"  Response: {response.text[:200]}...")
    except requests.exceptions.ConnectionError:
        print("✗ Root endpoint (/) - Connection refused")
    except Exception as e:
        print(f"✗ Root endpoint (/) - Error: {e}")
    
    # Test 2: Device status endpoint
    try:
        response = requests.get(f"{base_url}/device_status/", timeout=5)
        print(f"✓ Device status endpoint (/device_status/) - Status: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  Response: {json.dumps(data, indent=2)}")
            except:
                print(f"  Response: {response.text[:200]}...")
        else:
            print(f"  Response: {response.text}")
    except requests.exceptions.ConnectionError:
        print("✗ Device status endpoint (/device_status/) - Connection refused")
    except Exception as e:
        print(f"✗ Device status endpoint (/device_status/) - Error: {e}")
    
    # Test 3: Try to access WebSocket endpoint via HTTP (should fail but show if server is there)
    try:
        response = requests.get(f"{base_url}/ws", timeout=5)
        print(f"✓ WebSocket endpoint (/ws) via HTTP - Status: {response.status_code}")
        print(f"  Note: This should return 404 or 405 for WebSocket endpoints")
    except requests.exceptions.ConnectionError:
        print("✗ WebSocket endpoint (/ws) via HTTP - Connection refused")
    except Exception as e:
        print(f"✗ WebSocket endpoint (/ws) via HTTP - Error: {e}")
    
    # Test 4: Check if server is running on localhost
    try:
        response = requests.get("http://localhost:8000/device_status/", timeout=5)
        print(f"✓ Localhost device status - Status: {response.status_code}")
        print("  Server is running locally")
    except:
        print("✗ Localhost device status - Not accessible")
        print("  Server is not running locally")

if __name__ == "__main__":
    test_server() 