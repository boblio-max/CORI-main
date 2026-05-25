from adafruit_servokit import ServoKit

channels = 16
kit = ServoKit(channels=channels)

for i in range(channels):
    kit.servo[i].angle = 90
    