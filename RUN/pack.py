# USED TO PUT THE ARM INTO A SAFE POSITION FOR TRANSPORT OR STORAGE
try:
    from adafruit_servokit import ServoKit
except Exception as exc:
    ServoKit = None
    print(f"Warning: adafruit_servokit unavailable: {exc}")

if ServoKit is not None:
    channels = 16
    kit = ServoKit(channels=channels)

    # Set all positional servos to packing pose
    kit.servo[15].angle = 90
    kit.servo[14].angle = 20
    kit.servo[13].angle = 90
    kit.servo[12].angle = 70
    kit.servo[11].angle = 90
    
    # Set continuous servo claw to neutral (stopped)
    kit.continuous_servo[10].throttle = 0.0
else:
    print("Cannot run pack.py because adafruit_servokit is unavailable.")   
