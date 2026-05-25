import sys
import os
import asyncio
import json
import websockets
from adafruit_servokit import ServoKit
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import config
import socket

kit = ServoKit(channels=16)
SERVER_IP = socket.gethostbyname(socket.gethostname())

async def main():
    uri = f"ws://{SERVER_IP}:8765"
    
    servo_mapping = {
        "A1": config.SERVO_MAP['base'],       # Base rotation
        "A2": config.SERVO_MAP['shoulder'],   # Shoulder angle
        "A3": config.SERVO_MAP['elbow'],      # Elbow angle
        "A4": config.SERVO_MAP['wrist'],      # Wrist angle
        "A5": config.SERVO_MAP['spare'],      # Wrist roll
        "A6": config.SERVO_MAP['claw']        # Claw gripper
    }
    
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket server.")
        while True:
            packet = await websocket.recv()
            float_array = json.loads(packet)
            print("Received angles:", float_array)
            
            for key, val in float_array.items():
                if key in servo_mapping:
                    inverted_val = 180 - float(val)
                    clamped_val = max(0, min(180, inverted_val))
                    kit.servo[servo_mapping[key]].angle = clamped_val

asyncio.run(main())