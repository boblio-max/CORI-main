import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import urllib.request
import math
import numpy as np
import asyncio
import json
from servers import ws_client
from Robot_math import ik_solver
import threading

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

def in_range(val1, val2, margin):
    return abs(val1 - val2) <= margin

cap = cv2.VideoCapture(0)
ts = 0
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

angles = [90, 90, 90, 90, 90, 90] 
is_rotating = False

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

WORKSPACE_SCALE_X = 0.5  
WORKSPACE_SCALE_Y = 0.5 
MAX_EXPECTED_Z = 300.0

solver = ik_solver.IKSolver()
i=0
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
        cv2.line(frame, (630, 360), (650, 360), (255, 0, 0), 2)
        cv2.line(frame, (640, 350), (640, 370), (255, 0, 0), 2)
        
        if latest_result and latest_result.hand_landmarks:
            for hand_landmarks in latest_result.hand_landmarks:
                pts = [(int(lm.x * f_w), int(lm.y * h)) for lm in hand_landmarks]
                
                a,b = pts[12]
                x,y = pts[9]
                    
                for c_a, c_b in CONNECTIONS:
                    cv2.line(frame, pts[c_a], pts[c_b], (0, 255, 0), 2)
                for pt in pts:
                    cv2.circle(frame, pt, 4, (0, 0, 255), -1)
                
                if pts:
                    x_coords = [p[0] for p in pts]
                    y_coords = [p[1] for p in pts]
                    x1, y1 = min(x_coords) - 20, min(y_coords) - 20
                    x2, y2 = max(x_coords) + 20, max(y_coords) + 20
                    
                    bottomx, bottomy = pts[0]
                    
                    cv2.line(frame,pts[0],pts[9], (0,0,255), 2)
                    
                    angles[5] = 0
                    
                    
                    if in_range(pts[8][0], pts[7][0], 15) and in_range(pts[8][1], pts[7][1], 15) and in_range(pts[12][0], pts[11][0], 15) and in_range(pts[12][1], pts[11][1], 15) and in_range(pts[16][0], pts[15][0], 15) and in_range(pts[16][1], pts[15][1], 15) and in_range(pts[20][0], pts[19][0], 15) and in_range(pts[20][1], pts[19][1], 15):
                        print(f"grab {i}")
                        i += 1
                        angles[5] = 1
                    

                    # if in_range(pts[12][0], pts[11][0], 15) and in_range(pts[12][1], pts[11][1], 15) and in_range(pts[16][0], pts[15][0], 15) and in_range(pts[16][1], pts[15][1], 15) and in_range(pts[20][0], pts[19][0], 15) and in_range(pts[20][1], pts[19][1], 15):
                    #     print("point")
                    #     pass

                    center_x, center_y = 640, 720
                    target_x, target_y = pts[9]
                    raw_x = target_x - center_x
                    raw_y = target_y  - center_y
                    
                    
                    b_hand = np.array(pts[0])
                    hand = np.array(pts[9])  
                    hand_size_pixels = np.linalg.norm(b_hand - hand)
                    
                    if hand_size_pixels == 0: 
                        hand_size_pixels = 1
                        
                    
                    scaled_x = float(raw_x * WORKSPACE_SCALE_X)
                    scaled_y = float(raw_y * WORKSPACE_SCALE_Y)
                    scaled_z = -float(MAX_EXPECTED_Z - (hand_size_pixels * 1.2))
                    
                    print(f"Robot Vector: X: {scaled_x:.2f}, Y: {scaled_y:.2f}, Z: {scaled_z:.2f}")
                    
                    # 5. Pass clean, signed vectors to your IK solver
                    try:
                        angles_dict = solver.solve_angles(scaled_x, scaled_y, scaled_z)
                        
                        angles[0] = int(angles_dict.get('A1', 90))
                        angles[1] = int(angles_dict.get('A2', 90))
                        angles[2] = int(angles_dict.get('A3', 90))
                        angles[3] = int(angles_dict.get('A4', 90))
                    except Exception as e:
                        print(f"IK Target Out of Bounds: {e}")
                        
                    joint_angles = angles

                    key = cv2.waitKey(1) & 0xFF
                     
                    if key == ord('r'):
                        is_rotating = True
                    if key == ord('s'):
                        is_rotating = False
                    
                    with ws_client.data_lock:
                        ws_client.data["A1"] = 180 - math.fabs(joint_angles[0]) 
                        ws_client.data["A2"] = 180 - math.fabs(joint_angles[1])
                        ws_client.data["A3"] = 180 - math.fabs(joint_angles[2])
                        ws_client.data["A4"] = 180 - math.fabs(joint_angles[3])
                        ws_client.data["A5"] = 180 - math.fabs(joint_angles[4])
                        ws_client.data["A6"] = 180 - math.fabs(joint_angles[5])
    
        cv2.imshow("Hand Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
cap.release()
cv2.destroyAllWindows()