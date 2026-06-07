import socket

SERVER_HOST = r"192.168.1.20"
SERVER_PORT = 8765

SERVO_MAP = {
    'base': 15,          # A1: Base rotation
    'shoulder': 14,      # A2: Shoulder
    'elbow': 13,         # A3: Elbow
    'wrist': 12,        # A4: Wrist
    'roll': 11,          # A5: Wrist roll    
    'claw': 10           # Claw/Grabber
    
}

SERVO_INDICES = [
    SERVO_MAP['base'],
    SERVO_MAP['shoulder'],
    SERVO_MAP['elbow'],
    SERVO_MAP['wrist'],
    SERVO_MAP['roll'],
    SERVO_MAP['claw']
]

SAFE_POSE = [90.0, 90.0, 90.0, 90.0, 90.0, 0.0]

SERVO_MIN_ANGLE = 0
SERVO_MAX_ANGLE = 180
