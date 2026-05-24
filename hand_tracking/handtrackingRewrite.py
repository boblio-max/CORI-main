import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import urllib.request
import math
import numpy as np
import json
from servers import ws_client
from Robot_math import ik_solverREWRITE
import threading

# Start websocket server
threading.Thread(target=ws_client.start_server, daemon=True).start()

latest_result = None

try:
    from core.config import SERVER_HOST, SERVER_PORT
except ImportError:
    SERVER_HOST = "192.168.1.20"
    SERVER_PORT = 8765
    print("Warning: Could not import core.config, using defaults.")
    
CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17)
]

cap = cv2.VideoCapture(0)
ts = 0
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# Default angles for 6-axis setup
angles = [90, 90, 90, 90, 90, 0] 

# Initialize the IK solver
solver = ik_solverREWRITE.IKSolver(L=1.5)

MODEL = "hand_landmarker.task"
if not os.path.exists(MODEL):
    print("Downloading model...")
    urllib.request.urlretrieve(
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
        MODEL
    )
    print("Done.")

def callback(result, output_image, timestamp_ms):
    global latest_result
    latest_result = result
    
options = vision.HandLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=MODEL),
    running_mode=vision.RunningMode.LIVE_STREAM,
    result_callback=callback
)

# Lock state
is_locked = False

with vision.HandLandmarker.create_from_options(options) as landmarker:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, f_w = frame.shape[:2]
        
        # Only process hand tracking if NOT locked
        if not is_locked:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            landmarker.detect_async(mp_image, ts)
            ts += 1
            
            if latest_result and latest_result.hand_landmarks:
                for hand_landmarks in latest_result.hand_landmarks:
                    pts = [(int(lm.x * f_w), int(lm.y * h)) for lm in hand_landmarks]
                    
                    # Draw skeleton
                    for c_a, c_b in CONNECTIONS:
                        cv2.line(frame, pts[c_a], pts[c_b], (0, 255, 0), 2)
                    for pt in pts:
                        cv2.circle(frame, pt, 4, (0, 0, 255), -1)
                    
                    # Coordinate mapping
                    x_coords = [p[0] for p in pts]
                    y_coords = [p[1] for p in pts]
                    x1, y1 = max(0, min(x_coords)), max(0, min(y_coords))
                    x2, y2 = min(f_w, max(x_coords)), min(h, max(y_coords))
                    
                    ref_x, ref_z = pts[9]
                    scaled_x = (ref_x - 640) / 640 * 1.5
                    scaled_z = (720 - ref_z) / 720 * 3.0
                    
                    area = (x2 - x1) * (y2 - y1)
                    min_area, max_area = 20000, 200000
                    clamped_area = np.clip(area, min_area, max_area)
                    scaled_y = ((clamped_area - min_area) / (max_area - min_area)) * 3.0
                    
                    try:
                        angles_dict = solver.solve_angles(scaled_x, scaled_y, scaled_z)
                        angles[0] = int(np.clip(angles_dict['A1'], 0, 180))
                        angles[1] = int(np.clip(angles_dict['A2'], 0, 180))
                        angles[2] = int(np.clip(angles_dict['A3'], 0, 180))
                        angles[3] = int(np.clip(angles_dict['A4'], 0, 180))
                    except Exception:
                        pass

                    # Wrist Roll (A5)
                    dx = pts[9][0] - pts[0][0]
                    dy = pts[9][1] - pts[0][1]
                    roll_angle = np.degrees(np.arctan2(dx, -dy)) + 90
                    angles[4] = int(np.clip(roll_angle, 0, 180))

                    # Gripper (A6)
                    dist_pinch = math.hypot(pts[4][0] - pts[8][0], pts[4][1] - pts[8][1])
                    angles[5] = 180 if dist_pinch < 60 else 0

                    # Update shared data
                    with ws_client.data_lock:
                        ws_client.data["A1"] = angles[0]
                        ws_client.data["A2"] = angles[1]
                        ws_client.data["A3"] = angles[2]
                        ws_client.data["A4"] = angles[3]
                        ws_client.data["A5"] = angles[4]
                        ws_client.data["A6"] = angles[5]
        
        # Display Status
        status_text = "LOCKED" if is_locked else "TRACKING"
        status_color = (0, 0, 255) if is_locked else (0, 255, 0)
        cv2.putText(frame, f"STATUS: {status_text} (Press 'L' to Toggle)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        
        if not is_locked:
            cv2.putText(frame, f"A1:{angles[0]} A2:{angles[1]} A3:{angles[2]} A4:{angles[3]} A5:{angles[4]} A6:{angles[5]}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        cv2.imshow("CORI 6-Axis Hand Tracking", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('l'):
            is_locked = not is_locked
            print(f"Movement {'Locked' if is_locked else 'Unlocked'}")
            
cap.release()
cv2.destroyAllWindows()
