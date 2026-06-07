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
SERVER_IP = config.SERVER_HOST

async def main():
    uri = f"ws://{SERVER_IP}:8765"
    
    servo_mapping = {
        "A1": config.SERVO_MAP['base'],       # Base rotation
        "A2": config.SERVO_MAP['shoulder'],   # Shoulder angle
        "A3": config.SERVO_MAP['elbow'],      # Elbow angle
        "A4": config.SERVO_MAP['wrist'],      # Wrist angle
        "A6": config.SERVO_MAP['roll'],      # Wrist roll
        "A7": config.SERVO_MAP['claw']        # Claw gripper
    }
    
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket server.")
        while True:
            packet = await websocket.recv()
            float_array = json.loads(packet)
            print("Received angles:", float_array)

            for key in ['A1', 'A2', 'A3', 'A4', 'A5']:
                if key in servo_mapping:
                    val = float(float_array[key])
                    clamped_val = max(0, min(180, val))
                    kit.servo[servo_mapping[key]].angle = clamped_val
            
            # Set continuous claw (A6) throttle
            kit.continuous_servo[servo_mapping["A6"]].throttle = float(float_array['A6'])

asyncio.run(main())