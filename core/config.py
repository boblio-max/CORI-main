SERVER_HOST = "192.168.1.20" 
SERVER_PORT = 8765

SERVO_MAP = {
    'base': 11,          # A1: Base rotation
    'shoulder': 12,      # A2: Shoulder
    'elbow': 13,         # A3: Elbow
    'wrist': 14,         # A4: Wrist
    'claw': 15,          # Claw/Grabber
    'spare': 10          # Extra servo
}

SERVO_INDICES = [
    SERVO_MAP['base'],
    SERVO_MAP['shoulder'],
    SERVO_MAP['elbow'],
    SERVO_MAP['wrist'],
    SERVO_MAP['claw'],
    SERVO_MAP['spare']
]

SAFE_POSE = [180.0, 180.0, 90.0, 90.0, 0.0, 0.0]

SERVO_MIN_ANGLE = 0
SERVO_MAX_ANGLE = 180
