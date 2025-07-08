#!/usr/bin/env python3
"""
Test script to discover what routes are available on the server
"""
import requests
import json

def test_server_routes():
    base_url = "http://192.168.2.1:8000"
    
    print("Testing Server Routes")
    print("=" * 50)
    
    # Common FastAPI routes to test
    routes_to_test = [
        "/",
        "/docs",
        "/openapi.json",
        "/device_status/",
        "/device_health/",
        "/send_command/",
        "/ws",
        "/api/",
        "/health",
        "/status"
    ]
    
    for route in routes_to_test:
        try:
            response = requests.get(f"{base_url}{route}", timeout=5)
            print(f"✓ {route} - Status: {response.status_code}")
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"  Response: {json.dumps(data, indent=2)[:200]}...")
                except:
                    print(f"  Response: {response.text[:100]}...")
            elif response.status_code == 404:
                print(f"  Route not found")
            elif response.status_code == 405:
                print(f"  Method not allowed (might be POST only)")
            else:
                print(f"  Response: {response.text[:100]}...")
        except requests.exceptions.ConnectionError:
            print(f"✗ {route} - Connection refused")
        except Exception as e:
            print(f"✗ {route} - Error: {e}")
    
    print("\n" + "=" * 50)
    print("Analysis:")
    print("- If /docs returns 200, it's a FastAPI server with auto-generated docs")
    print("- If /openapi.json returns 200, it's a FastAPI server with OpenAPI spec")
    print("- If /ws returns 404, the WebSocket endpoint is not registered")
    print("- If /device_status/ returns 200, it's likely our MCU firmware")

if __name__ == "__main__":
    test_server_routes() 