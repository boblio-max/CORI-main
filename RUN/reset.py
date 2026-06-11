# USED TO RESET THE ARM TO A SAFE POSITION IN CASE OF EMERGENCY OR MALFUNCTION
# ALSO USED OUTSIDE OF THE DASHBOARD AND THE HANDTRACKING
try:
    from adafruit_servokit import ServoKit
except Exception as exc:
    ServoKit = None
    print(f"Warning: adafruit_servokit unavailable: {exc}")

if ServoKit is not None:
    channels = 16
    kit = ServoKit(channels=channels)

    # Reset all positional servos to 90 degrees, skip channel 10 (continuous servo claw)
    for i in range(channels):
        if i != 10:  # Skip the continuous servo channel
            kit.servo[i].angle = 90
    
    # Reset the continuous servo to neutral (0 throttle)
    kit.continuous_servo[10].throttle = 0.0
else:
    print("Cannot run reset.py because adafruit_servokit is unavailable.")
