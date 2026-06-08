# Imports
import sys, os

# Add parent directory to path for imports
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

# Start WebSocket server in a separate thread
threading.Thread(target=ws_client.start_server, daemon=True).start()

# Gets the local IP address of the machine
local_ip = socket.gethostbyname(socket.gethostname())
print(local_ip)

latest_result = None

# Sets the server IP and port for WebSocket communication
SERVER_HOST = local_ip
SERVER_PORT = 8765
print("Warning: Could not import core.config, using defaults.")
    
# Hand landmark connections for drawing
CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17)
]

# Function to check if two points are within a certain margin for gesture recognition
def in_range(val1, val2, margin):
    return abs(val1 - val2) <= margin

# Initialize video capture and set properties
cap = cv2.VideoCapture(0)
ts = 0
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# Initialize angles and state variables
# A6 (index 5) is the claw throttle: -1.0 = open, 0.0 = stop, +1.0 = close
angles = [90, 90, 90, 90, 90, 0.0]
is_rotating = False

# Load the hand landmark model, downloading it if it doesn't exist
MODEL = "hand_landmarker.task"
if not os.path.exists(MODEL):
    print("Downloading model...")
    urllib.request.urlretrieve(
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
        MODEL
    )
    print("Done.")

# Callback function to receive hand landmark results from the MediaPipe model
def callback(result, output_image, timestamp_ms):
    global latest_result
    latest_result = result
    
# Function to map a value from one range to another, used for scaling hand positions to servo angles
def map_value(value, left_min, left_max, right_min, right_max):
    left_span = left_max - left_min
    right_span = right_max - right_min
    value_scaled = float(value - left_min) / float(left_span)
    return right_min + (value_scaled * right_span)

# Set up MediaPipe hand landmarker options for live stream processing
options = vision.HandLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=MODEL),
    running_mode=vision.RunningMode.LIVE_STREAM,
    result_callback=callback
)

# Configuration constants for servo control and workspace scaling
WORKSPACE_SCALE_X = 0.5  
WORKSPACE_SCALE_Y = 0.5 
MAX_EXPECTED_Z = 300.0

# Constants
grab = False
i=0
locked = False
locked_angles = None

# Main loop to process video frames and control the robotic arm based on hand landmarks
with vision.HandLandmarker.create_from_options(options) as landmarker:
    # Loop to read video frames and process hand landmarks
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Flip the frame horizontally for a mirror effect and convert to RGB for MediaPipe processing
        frame = cv2.flip(frame, 1)
        h, f_w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        landmarker.detect_async(mp_image, ts)
        ts += 1
        cv2.line(frame, (630, 360), (650, 360), (255, 0, 0), 2)
        cv2.line(frame, (640, 350), (640, 370), (255, 0, 0), 2)
        
        # if the model has detected hand landmarks, process them to control the robotic arm
        if latest_result and latest_result.hand_landmarks:
            for hand_landmarks in latest_result.hand_landmarks:
                
                # Gets the points of the hand landmarks and scales them to the frame size
                pts = [(int(lm.x * f_w), int(lm.y * h)) for lm in hand_landmarks]
                
                # gets the points from the middle of your hand and the tip of your middle finger to calculate distance and angle for arm control
                a,b = pts[12]
                x,y = pts[9]
                
                # Draws the hand landmarks and connections on the video frame for visualization
                for c_a, c_b in CONNECTIONS:
                    cv2.line(frame, pts[c_a], pts[c_b], (255, 255, 0), 2)
                for pt in pts:
                    cv2.circle(frame, pt, 4, (255, 255, 255), -1)
                
                # If there are points...
                if pts:

                    # Splits the x and y coordinates of the hand landmarks into separate lists to calculate the bounding box of the hand
                    x_coords = [p[0] for p in pts]
                    y_coords = [p[1] for p in pts]

                    # Calculates the bounding box of the hand by finding the minimum and maximum x and y coordinates, with some padding
                    x1, y1 = min(x_coords) - 20, min(y_coords) - 20
                    x2, y2 = max(x_coords) + 20, max(y_coords) + 20
                    
                    # Gets the coordinates of the wrist (landmark 0) to use as a reference point for arm control
                    bottomx, bottomy = pts[0]
                    
                    # Draws a line from the wrist to the middle finger tip for visualization
                    cv2.line(frame,pts[0],pts[9], (0,0,255), 2)
                    
                    # Standardize A6 to -1..1: +1 close, -1 open, 0 stop
                    angles[5] = 1.0 if grab else -1.0
                    
                    # HAND GUESTURE RECOGNITION:

                    # Check for grab gesture
                    if in_range(pts[8][0], pts[7][0], 15) and in_range(pts[8][1], pts[7][1], 15) and in_range(pts[12][0], pts[11][0], 15) and in_range(pts[12][1], pts[11][1], 15) and in_range(pts[16][0], pts[15][0], 15) and in_range(pts[16][1], pts[15][1], 15) and in_range(pts[20][0], pts[19][0], 15) and in_range(pts[20][1], pts[19][1], 15):
                        # print(f"grab {i}")
                        grab = not grab
                        

                    
                    # Check for thumb up gesture
                    thumb_up = pts[4][1] < pts[0][1] - 30 
                    tolerance = 60
                    fingers_curled = (
                        in_range(pts[8][0], pts[5][0], 35) and in_range(pts[8][1], pts[5][1], tolerance) and  
                        in_range(pts[12][0], pts[9][0], 35) and in_range(pts[12][1], pts[9][1], tolerance) and 
                        in_range(pts[16][0], pts[13][0], 35) and in_range(pts[16][1], pts[13][1], tolerance) and 
                        in_range(pts[20][0], pts[17][0], 35) and in_range(pts[20][1], pts[17][1], tolerance)   
                    )

                    if thumb_up and fingers_curled:
                        for i in range(5):
                            angles[i] = 90
                    

                    # Check for OK gesture
                    mid_finger_up = pts[12][1] < pts[0][1] - 30
                    ring_finger_up = pts[16][1] < pts[0][1] - 30 and pts[20][1] < pts[0][1] - 30
                    pinky_up = pts[20][1] < pts[0][1] - 30

                    ok_gesture = in_range(pts[8][0], pts[4][0], 55) and in_range(pts[8][1], pts[4][1], 55) and mid_finger_up and ring_finger_up and pinky_up
                    if ok_gesture:
                        for c_a, c_b in CONNECTIONS:
                            cv2.line(frame, pts[c_a], pts[c_b], (255, 255, 0), 40)
                            grab = not grab
                        for pt in pts:
                            cv2.circle(frame, pt, 20, (255, 255, 0), -1)
                    

                    # Check for point gesture
                    if in_range(pts[12][0], pts[11][0], 15) and in_range(pts[12][1], pts[11][1], 15) and in_range(pts[16][0], pts[15][0], 15) and in_range(pts[16][1], pts[15][1], 15) and in_range(pts[20][0], pts[19][0], 15) and in_range(pts[20][1], pts[19][1], 15):
                        print("point")
                        pass
                    
                    
                    # Check for faze symbol (Damian suggestion)
                    pointer_finger_up = pts[8][1] < pts[0][1] - 30
                    if in_range(pts[11][0], pts[3][0], 35) and in_range(pts[11][1], pts[3][1], 35):
                        print("faze")
                    center = (640, 360)

                    # ensure consistent mapping: grab -> +1 (close), not-grab -> -1 (open)
                    if grab:
                        angles[5] = 1.0
                    else:
                        angles[5] = -1.0
                    # gets the coordinates of the wrist (landmark 0) and the middle of the palm (landmark 9) to calculate the distance and angle between them for controlling the arm's position and orientation
                    x0, y0 = pts[0]
                    x9, y9 = x, y
                    
                    # Calculate the distance and angle between the wrist and the middle finger tip to use for controlling the robotic arm's position with scaling based on the frame size
                    # FOR X AXIS
                    # As your hand moves left and right, we calculate the distance from the center of the frame,
                    # Then we scale to a range of 0 to 180 degrees for the base rotation of the robotic arm, with 90 degrees being centered. 

                    # FOR Y AXIS 
                    # As your hand moves up and dow, we calculate the distance from the top to the hand center,
                    # then it creates a general angle for the total of the angles,
                    # and then from the top down the angles spin down from the wrist to the shoulder
                    # with certain thresholds

                    # FOR Z AXIS
                    # As your hand moves forward and backward, we calculate the distance from the wrist to the middle finger tip,
                    # then we scale that distance to control the extension of the arm, with closer being more
                    # Finally, we move certain angles based on how close or far the hand is to create a more natural movement,
                    # with the arm extending more as the hand moves forward and retracting as it moves back



                    dx = x9 - x0
                    dy = y9 - y0
                    dist_09 = math.hypot(dx, dy)
                    rot_angle_09 = (math.degrees(math.atan2(dy, dx)) + 360) % 360

                    #print(dist_09, rot_angle_09)

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
                    
                    # set_move = 5
                    # if dist_09 > 250:
                    #     scale = dist_09 / 250
                    #     angles[1] = max(0, min(180, angles[1] + set_move * scale))
                    #     angles[2] = max(0, min(180, angles[2] - (set_move * scale)/2))
                    #     angles[3] = max(0, min(180, angles[3] - (set_move * scale)/2))

                    # elif dist_09 < 250:
                    #     scale = dist_09 / 250
                    #     angles[1] = max(0, min(180, angles[1] + set_move * scale))
                    #     angles[2] = max(0, min(180, angles[2] - (set_move * scale)/2))
                    #     angles[3] = max(0, min(180, angles[3] - (set_move * scale)/2))

                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('r'):
                        is_rotating = True
                    if key == ord('s'):
                        is_rotating = False
                    # Toggle lock with 'l' or 'L' — freeze robot pose
                    if key == ord('l') or key == ord('L'):
                        locked = not locked
                        if locked:
                            locked_angles = list(angles)
                            print("Robot locked — holding current pose")
                        else:
                            locked_angles = None
                            print("Robot unlocked — live control resumed")
                    
                    # print(float(angles[5]), 180 - float(angles[1]), 180 - float(angles[2]), 180 - float(angles[3]), float(angles[0]), final_x_val)
                    # If locked, override outgoing angles with snapshot
                    out_angles = locked_angles if locked and locked_angles is not None else angles
                    print(float(out_angles[0]), float(out_angles[3]), float(out_angles[2]), float(out_angles[1]), float(out_angles[4]), float(out_angles[5]))
                    with ws_client.data_lock:
                        ws_client.data["A1"] = float(out_angles[0])
                        ws_client.data["A2"] = float(out_angles[3])
                        ws_client.data["A3"] = float(out_angles[2])
                        ws_client.data["A4"] = float(out_angles[1])
                        ws_client.data["A5"] = float(out_angles[4])
                        ws_client.data["A6"] = float(out_angles[5])
                        
        cv2.imshow("Hand Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
cap.release()
cv2.destroyAllWindows()