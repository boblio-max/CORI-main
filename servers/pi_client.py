import asyncio
import json
import websockets
from adafruit_servokit import ServoKit

kit = ServoKit(channels=16)
SERVER_IP = "192.168.1.20"

def get_key(index):
    mapping = {
        0: "A1",  # A1
        1: "A2",  # A2
        2: "A3",  # A3
        3: "A4",  # A4
        4: "A5",  # Gripper
        5: "A6"   # Wrist rotation
    }
    return mapping.get(index, index)
async def main():

    uri = f"ws://{SERVER_IP}:8765"
    async with websockets.connect(uri) as websocket:
        print("Connected")
        while True:
            packet = await websocket.recv()
            float_array = json.loads(packet)
            print("Received:", float_array)
            for i in range(min(6, len(float_array))):
                if float_array[get_key(i)] < 0:
                    float_array[get_key(i)] = 0
                elif float_array[get_key(i)] > 180:
                    float_array[get_key(i)] = 180
                kit.servo[15-i].angle = float_array[get_key(i)]

asyncio.run(main())