import socket

# Configuration for the robotic arm control server
SERVER_HOST = r"10.173.156.209"
SERVER_PORT = 8765

# Mapping of servo names to their corresponding GPIO pins
SERVO_MAP = {
    'base': 15,          # A1: Base rotation
    'shoulder': 14,      # A2: Shoulder
    'elbow': 13,         # A3: Elbow
    'wrist': 12,        # A4: Wrist
    'roll': 11,          # A5: Wrist roll    
    'claw': 10           # Claw/Grabber
    
}

# List of servo indices in the order they will be controlled
SERVO_INDICES = [
    SERVO_MAP['base'],
    SERVO_MAP['shoulder'],
    SERVO_MAP['elbow'],
    SERVO_MAP['wrist'],
    SERVO_MAP['roll'],
    SERVO_MAP['claw']
]

# Default safe pose for the robotic arm (all servos at 90 degrees)
SAFE_POSE = [90.0, 90.0, 90.0, 90.0, 90.0, 0.0]

# Servo angle limits
SERVO_MIN_ANGLE = 0
SERVO_MAX_ANGLE = 180

# If True, the claw is a continuous-rotation servo and expects throttle values
# in range -1.0..+1.0. If False, the claw is a positional servo and will
# receive mapped angles (0..180). Change this to match your hardware.
CLAW_CONTINUOUS = True
