import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import socket
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
local_ip = socket.gethostbyname(socket.gethostname())
print(local_ip)

SERVER_HOST = local_ip
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
    
def map_value(value, left_min, left_max, right_min, right_max):
    left_span = left_max - left_min
    right_span = right_max - right_min
    value_scaled = float(value - left_min) / float(left_span)
    return right_min + (value_scaled * right_span)

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

                    center = (640, 360)

                    dist_x  = center[0] - pts[9][0]
                    
                    scaled_val = 90 - (dist_x * (90 / 640))
                    final_x_val = max(0, min(180, scaled_val))
                    key = cv2.waitKey(1) & 0xFF
                    
                    angles[0] = final_x_val
                    target_total_pitch = map_value(pts[9][1], 0, 720, 270.0, 0.0)
                    
                    A2_min, A2_max = 0.0, 80.0
                    A3_min, A3_max = 0.0, 80.0
                    A4_min, A4_max = 0.0, 80.0

                    remaining_pitch = target_total_pitch
                    angles[3] = max(A4_min, min(A4_max, remaining_pitch))
                    remaining_pitch -= angles[3]
                    angles[2] = max(A3_min, min(A3_max, remaining_pitch))
                    remaining_pitch -= angles[2]
                    angles[1] = max(A2_min, min(A2_max, remaining_pitch))

                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('r'): 
                        is_rotating = True
                    if key == ord('s'): 
                        is_rotating = False
                    
                    with ws_client.data_lock:
                        ws_client.data["A1"] = float(180 if angles[5] == 1 else 90)
                        ws_client.data["A2"] = 180 - float(angles[1])
                        ws_client.data["A3"] = 180 - float(angles[2])
                        ws_client.data["A4"] = 180 - float(angles[3])
                        ws_client.data["A5"] = float(angles[0])
                        ws_client.data["A6"] =  final_x_val
        cv2.imshow("Hand Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
cap.release()
cv2.destroyAllWindows()