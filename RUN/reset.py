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

    for i in range(channels):
        kit.servo[i].angle = 90
else:
    print("Cannot run reset.py because adafruit_servokit is unavailable.")
    