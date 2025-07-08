#!/usr/bin/env python3
"""
Test script to check network connectivity and API server status
"""
import socket
import requests
import time
import json

def test_port(host, port):
    """Test if a port is open on a host"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"Error testing {host}:{port}: {e}")
        return False

def test_http_endpoint(host, port, endpoint="/"):
    """Test HTTP endpoint"""
    try:
        url = f"http://{host}:{port}{endpoint}"
        response = requests.get(url, timeout=5)
        return response.status_code, response.text
    except requests.exceptions.ConnectionError:
        return None, "Connection refused"
    except requests.exceptions.Timeout:
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

def main():
    print("Network Connectivity Test")
    print("=" * 50)
    
    # Test targets
    targets = [
        ("localhost", 8000),
        ("127.0.0.1", 8000),
        ("10.147.18.68", 8000),
        ("192.168.2.1", 8000),
    ]
    
    for host, port in targets:
        print(f"\nTesting {host}:{port}")
        print("-" * 30)
        
        # Test port connectivity
        if test_port(host, port):
            print(f"✓ Port {port} is OPEN on {host}")
            
            # Test HTTP endpoint
            status, response = test_http_endpoint(host, port, "/device_status/")
            if status:
                print(f"✓ HTTP endpoint responded with status {status}")
                try:
                    data = json.loads(response)
                    print(f"  Response: {json.dumps(data, indent=2)}")
                except:
                    print(f"  Response: {response[:200]}...")
            else:
                print(f"✗ HTTP endpoint failed: {response}")
        else:
            print(f"✗ Port {port} is CLOSED on {host}")
    
    print("\n" + "=" * 50)
    print("Recommendations:")
    print("1. If localhost:8000 is open, the API server is running locally")
    print("2. If 10.147.18.68:8000 is closed, the MCU server is not running")
    print("3. Check firewall settings if needed")
    print("4. Start the MCU firmware if it's not running")

if __name__ == "__main__":
    main() 