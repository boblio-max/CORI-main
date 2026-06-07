# IMPORTS
import asyncio
import json
import websockets
import threading
import socket

# Gets the local IP address of the machine to bind the WebSocket server to
local_ip = socket.gethostbyname(socket.gethostname()) 

# Global variables
# Locks the data so that only one thread can access it at a time
data_lock = threading.Lock()
clients = set()

# Initial servo angles for A1-A6 (base, shoulder, elbow, wrist, roll, claw)
data = {
    "A1": 90.0,
    "A2": 90.0,
    "A3": 90.0,
    "A4": 90.0,
    "A5": 90.0,
    "A6": 0.0
}

# WebSocket handler for incoming client connections
async def handler(websocket):
    print("Client connected")
    # Adds the new client to the set of connected clients
    clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        clients.remove(websocket)
        print("Client disconnected")

# Broadcast loop to send the current servo angles to all connected clients at ~60 FPS
async def broadcast_loop():
    while True:
        with data_lock:
            packet = json.dumps(data)
        dead_clients = set()
        for client in clients:
            try:
                await client.send(packet)
            except:
                dead_clients.add(client)
                
        clients.difference_update(dead_clients)
        await asyncio.sleep(0.016)

# Main function to start the WebSocket server and broadcast loop
async def send_server():
    server = await websockets.serve(handler, local_ip, 8765)
    print("Server running on port 8765")
    asyncio.create_task(broadcast_loop())
    await server.wait_closed()

# Function to start the server, can be called from other modules
def start_server():
    asyncio.run(send_server())