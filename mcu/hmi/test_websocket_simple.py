#!/usr/bin/env python3
"""
Simple WebSocket test for 10.147.18.68:8000/ws
"""
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://10.147.18.68:8000/ws"
    
    try:
        print(f"Connecting to: {uri}")
        async with websockets.connect(uri) as websocket:
            print("SUCCESS: WebSocket connected!")
            
            # Send a test message
            test_msg = {"type": "test", "message": "Hello"}
            await websocket.send(json.dumps(test_msg))
            print(f"Sent: {test_msg}")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"Received: {response}")
            except asyncio.TimeoutError:
                print("No response received within 5 seconds")
                
    except websockets.exceptions.InvalidStatus as e:
        print(f"ERROR: Server rejected WebSocket connection: {e}")
        print("This usually means the WebSocket endpoint /ws is not available")
    except websockets.exceptions.ConnectionRefused:
        print("ERROR: Connection refused - server not accepting WebSocket connections")
    except websockets.exceptions.InvalidURI:
        print("ERROR: Invalid WebSocket URI")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket()) 