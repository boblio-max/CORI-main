import socket

SERVER_HOST = socket.gethostbyname(socket.gethostname())
SERVER_PORT = 8765

SERVO_MAP = {
    'base': 16,          # A1: Base rotation
    'shoulder': 15,      # A2: Shoulder
    'elbow': 14,         # A3: Elbow
    'wrist1': 13,        # A4: Wrist
    "wrist2": 12,        # A5 Wrist 2 
    'roll': 11,          # A5: Wrist roll    
    'claw': 10           # Claw/Grabber
    
}

SERVO_INDICES = [
    SERVO_MAP['base'],
    SERVO_MAP['shoulder'],
    SERVO_MAP['elbow'],
    SERVO_MAP['wrist1'],
    SERVO_MAP['wrist2'],
    SERVO_MAP['roll'],
    SERVO_MAP['claw']
]

SAFE_POSE = [90.0, 90.0, 90.0, 90.0, 90.0, 90.0,  0.0]

SERVO_MIN_ANGLE = 0
SERVO_MAX_ANGLE = 180
