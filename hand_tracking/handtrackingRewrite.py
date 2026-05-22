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
from Robot_math import ik_solver
import threading

# Start websocket server
threading.Thread(target=ws_client.start_server, daemon=True).start()

latest_result = None

try:
    from core.config import SERVER_HOST, SERVER_PORT
except ImportError:
    SERVER_HOST = "10.173.196.156"
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

def in_range(val1, val2, margin):
    return abs(val1 - val2) <= margin

cap = cv2.VideoCapture(0)
ts = 0
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

angles = [180, 180, 90, 90, 0, 0] 
is_rotating = False

# Initialize the IK solver ONCE outside the loop
solver = ik_solver.IKSolver()

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

with vision.HandLandmarker.create_from_options(options) as landmarker:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, f_w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        landmarker.detect_async(mp_image, ts)
        ts += 1
        
        # Draw target crosshair in the center
        cv2.line(frame, (630, 360), (650, 360), (255, 0, 0), 2)
        cv2.line(frame, (640, 350), (640, 370), (255, 0, 0), 2)
        
        if latest_result and latest_result.hand_landmarks:
            for hand_landmarks in latest_result.hand_landmarks:
                pts = [(int(lm.x * f_w), int(lm.y * h)) for lm in hand_landmarks]
                
                # Draw skeleton
                for c_a, c_b in CONNECTIONS:
                    cv2.line(frame, pts[c_a], pts[c_b], (0, 255, 0), 2)
                for pt in pts:
                    cv2.circle(frame, pt, 4, (0, 0, 255), -1)
                
                # Bounding box calculations
                x_coords = [p[0] for p in pts]
                y_coords = [p[1] for p in pts]
                x1, y1 = max(0, min(x_coords) - 20), max(0, min(y_coords) - 20)
                x2, y2 = min(f_w, max(x_coords) + 20), min(h, max(y_coords) + 20)
                
                if not is_rotating:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                
                # Coordinate mapping (using MCP joint 9 as reference)
                x_c, z_c = pts[9]
                max_disx = 640   
                max_disz = 360 
                
                disx = x_c - 640
                disz = z_c - 360 # Usually vertical screen movement translates to robot Z
                
                # Depth calculation (Y) via bounding box area
                width_val = x2 - x1
                height_val = y2 - y1
                area = width_val * height_val   
                
                # Prevent negative or division by zero errors by clamping area
                min_expected_area = 40000 
                max_expected_area = 300000
                clamped_area = np.clip(area, min_expected_area, max_expected_area)
                
                # Map area directly to a 0.0 to 3.0 scale for physical robot workspace
                scaled_y = ((clamped_area - min_expected_area) / (max_expected_area - min_expected_area)) * 3.0
                scaled_x = (disx / max_disx) * 3.0
                scaled_z = (disz / max_disz) * 3.0 # Note: Check if your robot space inverts Z and Y
                
                # Execute Inverse Kinematics
                try:
                    angles_dict = solver.solve_angles(scaled_x, scaled_y, scaled_z)
                    angles[0] = int(angles_dict['A1'])
                    angles[1] = int(angles_dict['A2'])
                    angles[2] = int(angles_dict['A3'])
                    
                    # Wrist rotation logic handling
                    if is_rotating:
                        a, b = pts[12] # Tip of middle finger
                        x, y = pts[9]  # MCP joint
                        cv2.circle(frame, (x, y), 100, (255, 0, 0), 2)
                        if math.fabs(a - x) > 0:
                            distance = math.fabs((b - y)) / (math.fabs(a - x))
                            angle = np.cos((distance - 50) / 100 * math.pi) * 90
                            cv2.line(frame, (x, y), (a, b), (0, 255, 0), 2)
                            angles[3] = int(angle)
                    else:
                        angles[3] = int(angles_dict['A4'])
                        
                except Exception as e:
                    # Capture mathematical out-of-bounds errors from IK solver gracefully
                    pass

                # Gripper logic (Thumb tip 4 to Index tip 8)
                angles[4] = 180 if in_range(pts[4][0], pts[8][0], 25) and in_range(pts[4][1], pts[8][1], 25) else 0

                # Update shared server dictionary
                with ws_client.data_lock:
                    ws_client.data["A1"] = angles[0]
                    ws_client.data["A2"] = angles[1]
                    ws_client.data["A3"] = angles[2]
                    ws_client.data["A4"] = angles[3]
                    ws_client.data["A5"] = angles[4]
                    ws_client.data["A6"] = angles[5]
        
        # Check keystrokes
        key = cv2.waitKey(1) & 0xFF
        if key == ord('r'):
            is_rotating = True
        elif key == ord('s'):
            is_rotating = False
        elif key == ord('q'):
            break
            
        cv2.imshow("Hand Tracking", frame)
        
cap.release()
cv2.destroyAllWindows()