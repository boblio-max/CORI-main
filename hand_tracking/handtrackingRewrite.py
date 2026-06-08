# AI VERSION OF THE HAND TRACKING - 
# Thing is I wrote changes to both the rewrite and regular myself, so they may look similar

# IMPORTS + PARENT DIRECTORY SETUP
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

# Start the WebSocket server in a separate thread
threading.Thread(target=ws_client.start_server, daemon=True).start()

# Initialize variables
latest_result = None
# Get the local IP address of the machine to set up the WebSocket server
local_ip = socket.gethostbyname(socket.gethostname())
print(local_ip)

# Set up the WebSocket server
SERVER_HOST = local_ip
SERVER_PORT = 8765
print("Warning: Could not import core.config, using defaults.")
    
# Define the connections between the hand landmarks for drawing the skeleton
CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17)
]

# Helper function to check if two values are within a certain margin of each other, used for gesture recognition
def in_range(val1, val2, margin):
    return abs(val1 - val2) <= margin

# Set up the video capture from the webcam
cap = cv2.VideoCapture(0)
ts = 0
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# Initialize the angles for the robot's joints, with 90 degrees as the default position for all joints 
# except the 0 degrees for the claw (open) and a flag to track whether the robot is currently rotating
angles = [90, 90, 90, 90, 90, 0.0] 
is_rotating = False

# Check if the hand landmark model file exists, and if not, download it from the specified URL
MODEL = "hand_landmarker.task"
if not os.path.exists(MODEL):
    print("Downloading model...")
    urllib.request.urlretrieve(
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
        MODEL
    )
    print("Done.")

# Define the callback function that will be called with the results from the hand landmark detection,
# which updates the latest_result variable with the new results
def callback(result, output_image, timestamp_ms):
    global latest_result
    latest_result = result
    
# Helper function to map a value from one range to another, 
# used for scaling the hand landmark positions to the robot's joint angles    
def map_value(value, left_min, left_max, right_min, right_max):
    left_span = left_max - left_min
    right_span = right_max - right_min
    value_scaled = float(value - left_min) / float(left_span)
    return right_min + (value_scaled * right_span)

# Set up the options for the hand landmark detection, including the model to use, the running mode, and the callback function
# to handle the results
options = vision.HandLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=MODEL),
    running_mode=vision.RunningMode.LIVE_STREAM,
    result_callback=callback
)

# Define the workspace scale and maximum expected Z value for the hand landmarks,
# which can be used to filter out unrealistic landmark positions
WORKSPACE_SCALE_X = 0.5  
WORKSPACE_SCALE_Y = 0.5 
MAX_EXPECTED_Z = 300.0

# Initialize the inverse kinematics solver, which will be used to calculate the robot's joint angles 
# based on the hand landmark positions
# This isn't used anymore, so it can be removed, but I'm keeping it here for now in case we want to use it again in the future
solver = ik_solver.IKSolver()
grab = False
i=0

# Create the hand landmark detection object using the specified options, 
# and start processing the video feed from the webcam
with vision.HandLandmarker.create_from_options(options) as landmarker:
    # Loop through the video feed, processing each frame to detect hand landmarks
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Flip the frame horizontally for a mirror effect, 
        # and convert the color space from BGR to RGB for processing with MediaPipe
        frame = cv2.flip(frame, 1)
        h, f_w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        
        # Run the hand landmark detection asynchronously,
        # which will call the callback function with the results when they are ready
        landmarker.detect_async(mp_image, ts)
        ts += 1
        cv2.line(frame, (630, 360), (650, 360), (255, 0, 0), 2)
        cv2.line(frame, (640, 350), (640, 370), (255, 0, 0), 2)
        
        # If there are results from the hand landmark detection, process them to extract the landmark positions,
        # draw the hand skeleton on the frame, and recognize specific gestures based on the landmark positions
        if latest_result and latest_result.hand_landmarks:
            for hand_landmarks in latest_result.hand_landmarks:
                # Convert the normalized landmark positions to pixel coordinates for drawing and gesture recognition
                pts = [(int(lm.x * f_w), int(lm.y * h)) for lm in hand_landmarks]
                
                # Get the positions of the middle of the hand, and the middle finger tip,
                # which are used for gesture recognition and controlling the robot's joints 
                a,b = pts[12]
                x,y = pts[9]
                    
                # Draw the hand skeleton by connecting the landmarks according to the defined connections,
                for c_a, c_b in CONNECTIONS:
                    cv2.line(frame, pts[c_a], pts[c_b], (255, 255, 0), 2)
                for pt in pts:
                    cv2.circle(frame, pt, 4, (255, 255, 255), -1)
                
                # If there are valid landmark positions, 
                # calculate the bounding box of the hand and recognize specific gestures based on the positions of the landmarks,
                # and use the distance from the bottom center to determine the angles of C.O.R.I
                if pts:
                    x_coords = [p[0] for p in pts]
                    y_coords = [p[1] for p in pts]
                    x1, y1 = min(x_coords) - 20, min(y_coords) - 20
                    x2, y2 = max(x_coords) + 20, max(y_coords) + 20
                    
                    bottomx, bottomy = pts[0]
                    
                    cv2.line(frame,pts[0],pts[9], (0,0,255), 2)
                    angles[5] = 0
                    
                    
                    # Check for grab gesture
                    if in_range(pts[8][0], pts[7][0], 15) and in_range(pts[8][1], pts[7][1], 15) and in_range(pts[12][0], pts[11][0], 15) and in_range(pts[12][1], pts[11][1], 15) and in_range(pts[16][0], pts[15][0], 15) and in_range(pts[16][1], pts[15][1], 15) and in_range(pts[20][0], pts[19][0], 15) and in_range(pts[20][1], pts[19][1], 15):
                        # print(f"grab {i}")
                        grab = not grab
                        if grab:
                            angles[5] = 1
                        else:
                            angles[5] = 0

                    
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

                    if in_range(pts[8][0], pts[4][0], 55) and in_range(pts[8][1], pts[4][1], 55) and mid_finger_up and ring_finger_up and pinky_up:
                        for c_a, c_b in CONNECTIONS:
                            cv2.line(frame, pts[c_a], pts[c_b], (255, 255, 0), 40)
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
                    
                    x0, y0 = pts[0]
                    x9, y9 = pts[9]

                    # Euclidean distance in pixels between wrist (0) and middle of palm (9)
                    dist_09 = math.sqrt((x9 - x0) ** 2 + (y9 - y0) ** 2)

                    
                    
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
                    
                    # Update angles based on "Z" distance
                    set_move = 5
                    if dist_09 > 250:
                        scale = dist_09 / 250
                        
                        angles[1] = angles[1] + set_move * scale
                        angles[2] = angles[2] - (set_move * scale)/2
                        angles[3] = angles[3] - (set_move * scale)/2
                    elif dist_09 < 250:
                        scale = dist_09 / 250
                        angles[1] = angles[1] + set_move * scale
                        angles[2] = angles[2] - (set_move * scale)/2
                        angles[3] = angles[3] - (set_move * scale)/2
                        
                    # Old tests for rotating control with 'R' and 'S' keys
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('r'): 
                        is_rotating = True
                    if key == ord('s'): 
                        is_rotating = False
                    
                    # Sending data to the pi_client through the WebSocket server, 
                    # directly updating the angles in ws_client and sending them
                    # print(f"angles: {[round(a, 1) for a in angles]}")
                    with ws_client.data_lock:
                        ws_client.data["A1"] = float(angles[0])
                        ws_client.data["A2"] = 180 - float(angles[1])
                        ws_client.data["A3"] = 180 - float(angles[2])
                        ws_client.data["A4"] = 180 - float(angles[3])
                        ws_client.data["A5"] = float(angles[4])
                        # Standardize A6: -1.0=open, 0.0=stop, +1.0=close
                        ws_client.data["A6"] = 0.0
                        ws_client.data["A7"] = float(180 if angles[5] == 1 else 90)
                        
        cv2.imshow("Hand Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
cap.release()
cv2.destroyAllWindows()