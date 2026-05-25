import asyncio
import json
import websockets
import threading
import socket

local_ip = socket.gethostbyname(socket.gethostname()) 

data_lock = threading.Lock()
clients = set()
data = {
    "A1": 90.0,
    "A2": 90.0,
    "A3": 90.0,
    "A4": 90.0,
    "A5": 90.0,
    "A6": 90.0
}

async def handler(websocket):
    print("Client connected")
    clients.add(websocket)

    try:
        await websocket.wait_closed()
    finally:
        clients.remove(websocket)
        print("Client disconnected")


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


async def send_server():
    server = await websockets.serve(handler, local_ip, 8765)
    print("Server running on port 8765")
    asyncio.create_task(broadcast_loop())
    await server.wait_closed()

def start_server():
    asyncio.run(send_server())