# USED TO PUT THE ARM INTO A SAFE POSITION FOR TRANSPORT OR STORAGE
from adafruit_servokit import ServoKit

channels = 16
kit = ServoKit(channels=channels)

kit.servo[15].angle = 90
kit.servo[14].angle = 20
kit.servo[13].angle = 90
kit.servo[12].angle = 70
kit.servo[11].angle = 90
kit.continuous_servo[10].throttle = 0