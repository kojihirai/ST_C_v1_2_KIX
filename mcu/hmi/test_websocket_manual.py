#!/usr/bin/env python3
"""
Manual WebSocket test with detailed error reporting
"""
import socket
import struct
import base64
import hashlib
import json

def test_websocket_manual():
    host = "192.168.2.1"
    port = 8000
    
    print(f"Testing WebSocket connection to {host}:{port}")
    print("=" * 50)
    
    # Step 1: Test basic TCP connection
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        print("✓ TCP connection successful")
        
        # Step 2: Send WebSocket handshake
        key = base64.b64encode(b"test-key-12345").decode()
        handshake = (
            f"GET /ws HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"\r\n"
        )
        
        print("Sending WebSocket handshake...")
        sock.send(handshake.encode())
        
        # Step 3: Read response
        response = sock.recv(1024).decode()
        print(f"Response received:")
        print(response)
        
        if "101 Switching Protocols" in response:
            print("✓ WebSocket handshake successful!")
            
            # Step 4: Send a test message
            test_msg = json.dumps({"type": "test", "message": "Hello"})
            print(f"Sending test message: {test_msg}")
            
            # Simple WebSocket frame (unmasked)
            frame = struct.pack('!BB', 0x81, len(test_msg)) + test_msg.encode()
            sock.send(frame)
            
            # Step 5: Try to read response
            try:
                response = sock.recv(1024)
                print(f"Received response: {response}")
            except socket.timeout:
                print("No response received (timeout)")
                
        elif "404 Not Found" in response:
            print("✗ WebSocket endpoint /ws not found")
            print("The server is running but doesn't have the WebSocket route")
        elif "405 Method Not Allowed" in response:
            print("✗ Method not allowed - might be a different server")
        else:
            print(f"✗ Unexpected response: {response}")
            
        sock.close()
        
    except socket.timeout:
        print("✗ Connection timeout")
    except ConnectionRefusedError:
        print("✗ Connection refused")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_websocket_manual() 