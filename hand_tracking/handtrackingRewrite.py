import sys, os
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import urllib.request
import math
import numpy as np
import threading
import json

# Ensure we can import from the parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from servers import ws_client
from Robot_math import ik_solverREWRITE
from core import config

# --- CRITICAL FIX: Ensure WebSocket data starts with SAFE_POSE ---
with ws_client.data_lock:
    ws_client.data = {
        "A1": config.SAFE_POSE[0],
        "A2": config.SAFE_POSE[1],
        "A3": config.SAFE_POSE[2],
        "A4": config.SAFE_POSE[3],
        "A5": config.SAFE_POSE[4],
        "A6": config.SAFE_POSE[5]
    }

# Start websocket server background thread
threading.Thread(target=ws_client.start_server, daemon=True).start()

# Initialize the IK solver (Match L with your robot/sim)
solver = ik_solverREWRITE.IKSolver(L=1.0)

latest_result = None
is_locked = False

# Mediapipe Connections for drawing
CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17)
]

# Model setup
MODEL = "hand_landmarker.task"
if not os.path.exists(MODEL):
    print("Downloading hand landmarker model...")
    urllib.request.urlretrieve(
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
        MODEL
    )

def callback(result, output_image, timestamp_ms):
    global latest_result
    latest_result = result

options = vision.HandLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=MODEL),
    running_mode=vision.RunningMode.LIVE_STREAM,
    result_callback=callback
)

# Camera setup
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
ts = 0

# Local tracking of angles (initialized to SAFE_POSE)
current_angles = list(config.SAFE_POSE)

print(f"System Initialized. Starting with SAFE_POSE: {current_angles}")

with vision.HandLandmarker.create_from_options(options) as landmarker:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, f_w = frame.shape[:2]
        
        if not is_locked:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            landmarker.detect_async(mp_image, ts)
            ts += 1
            
            if latest_result and latest_result.hand_landmarks:
                for hand_landmarks in latest_result.hand_landmarks:
                    pts = [(int(lm.x * f_w), int(lm.y * h)) for lm in hand_landmarks]
                    
                    # Draw skeleton for feedback
                    for c_a, c_b in CONNECTIONS:
                        cv2.line(frame, pts[c_a], pts[c_b], (0, 255, 0), 2)
                    for pt in pts:
                        cv2.circle(frame, pt, 4, (0, 0, 255), -1)
                    
                    # --- COORDINATE MAPPING FIX ---
                    # ref_x: Center is 640. Map to -1.0 to 1.0
                    # ref_z: Screen Y (up/down). Map to 0 to 2.0
                    ref_x, ref_z = pts[9]
                    
                    # Horizontal (X)
                    scaled_x = (ref_x - 640) / 640.0 * 1.5
                    
                    # Vertical (Z in IK space)
                    # Screen Y=0 is Top, Y=720 is Bottom.
                    # We want 0 at Bottom, 2.0 at Top.
                    scaled_z = (720 - ref_z) / 720.0 * 2.0
                    
                    # Depth (Y in IK space)
                    # Using hand area as a proxy for distance.
                    x_coords = [p[0] for p in pts]
                    y_coords = [p[1] for p in pts]
                    area = (max(x_coords) - min(x_coords)) * (max(y_coords) - min(y_coords))
                    
                    min_area, max_area = 30000, 250000
                    clamped_area = np.clip(area, min_area, max_area)
                    # Near (Large Area) -> Y=2.0, Far (Small Area) -> Y=0.5
                    scaled_y = 0.5 + ((clamped_area - min_area) / (max_area - min_area)) * 1.5
                    
                    # Solve for A1-A4
                    try:
                        # Use the rewrite solver which maps 0-180 correctly
                        angles_dict = solver.solve_angles(scaled_x, scaled_y, scaled_z)
                        
                        # Clamp and convert to int
                        current_angles[0] = int(np.clip(angles_dict['A1'], config.SERVO_MIN_ANGLE, config.SERVO_MAX_ANGLE))
                        current_angles[1] = int(np.clip(angles_dict['A2'], config.SERVO_MIN_ANGLE, config.SERVO_MAX_ANGLE))
                        current_angles[2] = int(np.clip(angles_dict['A3'], config.SERVO_MIN_ANGLE, config.SERVO_MAX_ANGLE))
                        current_angles[3] = int(np.clip(angles_dict['A4'], config.SERVO_MIN_ANGLE, config.SERVO_MAX_ANGLE))
                        
                        # Wrist Roll (A5)
                        dx = pts[9][0] - pts[0][0]
                        dy = pts[9][1] - pts[0][1]
                        roll_angle = np.degrees(np.arctan2(dx, -dy)) + 90
                        current_angles[4] = int(np.clip(roll_angle, config.SERVO_MIN_ANGLE, config.SERVO_MAX_ANGLE))

                        # Gripper (A6)
                        dist_pinch = math.hypot(pts[4][0] - pts[8][0], pts[4][1] - pts[8][1])
                        current_angles[5] = 180 if dist_pinch < 60 else 0

                        # Broadcast to Robot/Sim
                        with ws_client.data_lock:
                            ws_client.data["A1"] = float(current_angles[0])
                            ws_client.data["A2"] = float(current_angles[1])
                            ws_client.data["A3"] = float(current_angles[2])
                            ws_client.data["A4"] = float(current_angles[3])
                            ws_client.data["A5"] = float(current_angles[4])
                            ws_client.data["A6"] = float(current_angles[5])
                            
                    except Exception as e:
                        pass
        
        # UI Overlay
        status_text = "LOCKED" if is_locked else "TRACKING"
        status_color = (0, 0, 255) if is_locked else (0, 255, 0)
        cv2.putText(frame, f"STATUS: {status_text} (L to Toggle)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        cv2.putText(frame, f"IK: X:{scaled_x:.2f} Y:{scaled_y:.2f} Z:{scaled_z:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        cv2.putText(frame, f"Angles: {current_angles}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        cv2.imshow("CORI Working Hand Tracking", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('l'):
            is_locked = not is_locked
            
cap.release()
cv2.destroyAllWindows()
