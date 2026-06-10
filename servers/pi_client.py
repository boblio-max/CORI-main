# IMPORTS + PARENT MODULE SETUP
import sys
import os
import asyncio
import json
import websockets
import logging
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

# Logging
logging.basicConfig(level=logging.INFO, format="[pi_client] %(levelname)s: %(message)s")

if kit is None:
    logging.warning("ServoKit (adafruit_servokit) not available — servos will not be driven.")

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
        logging.info("Connected to WebSocket server.")
        # Log mapping for verification
        logging.info(f"Servo mapping: A5->channel {servo_mapping['A5']}, A6->channel {servo_mapping['A6']}")
        while True:
            # Recieves a packet containing the angles for A1-A6, which are expected to be in JSON format
            packet = await websocket.recv()
            
            # Converts the json format to an array
            float_array = json.loads(packet)
            print("Received angles:", float_array)

            # Control A1-A5 as standard positional servos
            for key in ['A1', 'A2', 'A3', 'A4', 'A5']:
                if key in servo_mapping:
                    try:
                        val = float(float_array.get(key, 90.0))
                    except Exception:
                        val = 90.0
                    clamped_val = max(0, min(180, val))
                    chan = servo_mapping[key]
                    if kit is not None:
                        try:
                            kit.servo[chan].angle = clamped_val
                        except Exception as e:
                            logging.warning(f"Failed to write angle to channel {chan}: {e}")

            # Control A6 (claw): either a continuous servo (throttle) or positional fallback
            claw_chan = servo_mapping["A6"]
            try:
                throttle = float(float_array.get('A6', 0.0))
            except Exception:
                throttle = 0.0

            if getattr(config, 'CLAW_CONTINUOUS', True):
                # Direct throttle for continuous servo
                if kit is not None:
                    try:
                        kit.continuous_servo[claw_chan].throttle = throttle
                    except Exception as e:
                        logging.warning(f"Failed to write throttle to continuous servo channel {claw_chan}: {e}")
                else:
                    logging.debug(f"CLAW throttle (sim): {throttle} on channel {claw_chan}")
            else:
                # Map throttle (-1..1) to angle (0..180) for positional servos
                mapped_angle = max(0, min(180, int(throttle * 90 + 90)))
                if kit is not None:
                    try:
                        kit.servo[claw_chan].angle = mapped_angle
                    except Exception as e:
                        logging.warning(f"Failed to write mapped claw angle to channel {claw_chan}: {e}")
                else:
                    logging.debug(f"CLAW angle (sim): {mapped_angle} on channel {claw_chan}")

if __name__ == "__main__":
    asyncio.run(main()) 