# USED TO RESET THE ARM TO A SAFE POSITION IN CASE OF EMERGENCY OR MALFUNCTION
# ALSO USED OUTSIDE OF THE DASHBOARD AND THE HANDTRACKING
from adafruit_servokit import ServoKit

channels = 16
kit = ServoKit(channels=channels)

for i in range(channels):
    kit.servo[i].angle = 90
    