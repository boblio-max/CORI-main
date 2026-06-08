# IMPORTS + PARENT MODULE SETUP
import sys
import os
import asyncio
import json
import websockets
try:
    from adafruit_servokit import ServoKit
except Exception as exc:
    ServoKit = None
    print(f"Warning: adafruit_servokit unavailable: {exc}")
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import config
import socket

# Initialize the ServoKit for controlling the servos
kit = ServoKit(channels=16) if ServoKit is not None else None
SERVER_IP = config.SERVER_HOST

async def main():
    uri = f"ws://{SERVER_IP}:8765"
    
    servo_mapping = {
        "A1": config.SERVO_MAP['base'],       # Base rotation
        "A2": config.SERVO_MAP['shoulder'],   # Shoulder angle
        "A3": config.SERVO_MAP['elbow'],      # Elbow angle
        "A4": config.SERVO_MAP['wrist'],      # Wrist angle
        "A5": config.SERVO_MAP['roll'],       # Wrist roll
        "A6": config.SERVO_MAP['claw']        # Claw gripper (continuous servo)
    }
    
    # Connect to the WebSocket server and continuously receive servo angle updates
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket server.")
        # Log mapping for verification
        print(f"Servo mapping: A5->channel {servo_mapping['A5']}, A6->channel {servo_mapping['A6']}")
        while True:
            # Recieves a packet containing the angles for A1-A6, which are expected to be in JSON format
            packet = await websocket.recv()
            
            # Converts the json format to an array
            float_array = json.loads(packet)
            print("Received angles:", float_array)

            # Control A1-A5 as standard positional servos
            # Runs C.O.R.I
            for key in ['A1', 'A2', 'A3', 'A4', 'A5']:
                if key in servo_mapping:
                    val = float(float_array[key])
                    clamped_val = max(0, min(180, val))
                    chan = servo_mapping[key]
                    kit.servo[chan].angle = clamped_val
                    

            # Control A6 as a continuous servo throttle (-1 to 1) for the claw
            claw_chan = servo_mapping["A6"]
            throttle = float(float_array['A6'])
            kit.continuous_servo[claw_chan].throttle = throttle

if __name__ == "__main__":
    asyncio.run(main()) 