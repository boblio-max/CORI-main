import asyncio
import json
import websockets
from adafruit_servokit import ServoKit

kit = ServoKit(channels=16)
SERVER_IP = "192.168.1.20"

async def main():

    uri = f"ws://{SERVER_IP}:8765"
    async with websockets.connect(uri) as websocket:
        print("Connected")
        while True:
            packet = await websocket.recv()
            float_array = json.loads(packet)
            print("Received:", float_array)
            for i in range(min(6, len(float_array))):
                kit.servo[15-i].angle = float_array[i]

asyncio.run(main())