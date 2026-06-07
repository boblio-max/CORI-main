# AI VERSION OF THE DASHBOARD -
# Thing is I wrote changes to both the rewrite and regular myself, so they may look similar

# Import necessary modules and set up paths
import sys, os
# Add parent directory to sys.path for module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pygame
import sys
import math
import os
import numpy as np
import asyncio
import json
import websockets
from Robot_math import ik_solver
from error_handling import errors
from servers import ws_client
import threading

# Start the WebSocket server in a separate thread
threading.Thread(target=ws_client.start_server, daemon=True).start()

# Initialize global variables and constants(NOT USED, NEED FIXING)
vector = ik_solver.IKSolver(L=1.0)

# Init pygame and joystick
pygame.init()
pygame.joystick.init()

# Set constants
width, height = 700, 700
screen = pygame.display.set_mode((width, height))
clock = pygame.time.Clock()
pygame.display.set_caption("C.O.R.I DASHBOARD")

L  = 1.0
A1 = 0
A2 = 0
A3 = 0
A4 = 0
x  = 0.5  

# Set colors
BACKGROUND  = (18, 18, 30)
ACCENT      = (0, 200, 255)
PANEL_BG    = (30, 30, 45)
TEXT_COLOR  = (220, 220, 255)
WARNING     = (255, 180, 50)
DANGER      = (255, 80, 80)
SUCCESS     = (80, 220, 150)
WHITE       = (255, 255, 255)
DIM         = (100, 100, 130)

CIRCLE_R      = 70
CIRCLE_BORDER = 3
NEEDLE_WIDTH  = 3
GAUGE_BG      = (40, 40, 60)

# list of logs for the robot to get displayed on the dashboard
logs = []

# Initialized fonts for rendering text on the dashboard
font = pygame.font.SysFont('Arial', 20, bold=True)
small_font = pygame.font.SysFont('Arial', 14)
logs_font = pygame.font.SysFont('Consolas', 15)

# Initialize joint angles 
joint_angles = [90.0, 90.0, 90.0, 90.0, 90.0, 90.0]

# Define positions for the gauges on the dashboard
col_xs      = [width // 4, width // 4 * 3]
row_ys      = [120, 280, 440]
circle_pos  = [
    (col_xs[0], row_ys[0]-30),  
    (col_xs[1], row_ys[0]-30), 
    (col_xs[0], row_ys[1]),  
    (col_xs[1], row_ys[1]),  
    (width // 2, row_ys[2]-30), 
]

# Gets the joysticks initialized 
joysticks = []
for i in range(pygame.joystick.get_count()):
    joy = pygame.joystick.Joystick(i)
    joy.init()
    joysticks.append(joy)

# More color initiialization for the buttons
red_button    = PANEL_BG
green_button  = PANEL_BG
blue_button   = PANEL_BG
yellow_button = PANEL_BG
WHITE         = (255, 255, 255)

# Toggle states for the buttons
is_clicked_ai = False
is_clicked    = False
is_clicked1   = False
is_clicked2   = False
is_clicked3   = False
running       = True

# DPAD constants for controlling the claw with the joystick's D-pad
DPAD_STEP = 1.5
DPAD_STEP_PER_SEC = 90.0
DEADZONE = 0.10

# Helper function to draw the rounded rectangles for the buttons and panels
def draw_rounded_rect(surface, rect, color, radius=10, border=0):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border > 0:
        pygame.draw.rect(surface, (255, 255, 255), rect, border, border_radius=radius)
        
# Helper function to convert the raw axis values from the joystick to angles for the robot's joints, 
# with a deadzone to prevent small movements from affecting the robot's position
def axis_to_angle(raw_axis):
    if abs(raw_axis) < DEADZONE:
        raw_axis = 0.0
    else:
        sign = 1 if raw_axis > 0 else -1
        raw_axis = sign * (abs(raw_axis) - DEADZONE) / (1.0 - DEADZONE)
    return 90.0 + raw_axis * 90.0

# Scales the claw angle from 0-180 degrees to a range of -1 to 1, where 90 degrees corresponds to 0 (No movement)
def scale_angle(angle_deg: float) -> float:
    """Map 0–180 degrees to -1–1, with 90 degrees -> 0."""
    return (angle_deg - 90.0) / 90.0

# Clamps the angle to ensure it stays within the valid range of 0 to 180 degrees for the robot's joints
def clamp(angle):
    return max(0, min(180, angle))

# Main loop  
while running:
    # limit the framerate to 60 FPS
    clock.tick(60)
    joystick_vector = (0.0, 0.0, 0.0)
    
    # Check for events such as joystick connections, button presses, and window closing
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        # Handle button presses from both the joystick and mouse clicks on the dashboard buttons, updating the state of the buttons and logging these actions
        elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.JOYBUTTONDOWN:
            x, y = pygame.mouse.get_pos() 
            ai_mode_rect = pygame.Rect(width // 2 - 90, height - 75, 80, 30)
            claw_rect    = pygame.Rect(width // 2 + 10, height - 75, 80, 30)
            home_rect    = pygame.Rect(width // 2 - 90, height - 35, 80, 30)
            pose_rect    = pygame.Rect(width // 2 + 10, height - 35, 80, 30)

            # Different buttons can be triggered by either a joystick button press 
            # or a mouse click on the corresponding area of the dashboard, allowing for flexible control options
            is_btn0 = (event.type == pygame.JOYBUTTONDOWN and event.button == 0) or \
                      (event.type == pygame.MOUSEBUTTONDOWN and claw_rect.collidepoint(x, y))
            is_btn1 = (event.type == pygame.JOYBUTTONDOWN and event.button == 1) or \
                      (event.type == pygame.MOUSEBUTTONDOWN and ai_mode_rect.collidepoint(x, y))
            is_btn2 = (event.type == pygame.JOYBUTTONDOWN and event.button == 2) or \
                      (event.type == pygame.MOUSEBUTTONDOWN and home_rect.collidepoint(x, y))
            is_btn3 = (event.type == pygame.JOYBUTTONDOWN and event.button == 3) or \
                      (event.type == pygame.MOUSEBUTTONDOWN and pose_rect.collidepoint(x, y))

            # Checks to see if the claw is activated or not, and toggles the is_clicked state
            if is_btn0:
                is_clicked = not is_clicked
                logs.append("Claw Activated" if is_clicked else "Claw Deactivated")
                joint_angles[5] = 180.0 if is_clicked else 0.0
                green_button = SUCCESS if is_clicked else PANEL_BG


            # Checks to see if the AI mode is activated or not, and toggles the is_clicked_ai state (THIS IS NOT IMPLEMENTED)
            elif is_btn1:
                is_clicked_ai = not is_clicked_ai
                logs.append("AI Mode " + ("Activated" if is_clicked_ai else "Deactivated"))
                red_button = DANGER if is_clicked_ai else PANEL_BG

            # Checks to see if the home position button is activated or not, and toggles the is_clicked2 state, which resets the robot's joints to a default position when activated
            elif is_btn2:
                is_clicked2 = not is_clicked2
                blue_button = ACCENT if is_clicked2 else PANEL_BG
                joint_angles[:5] = [90.0, 90.0, 90.0, 90.0, 90.0]
                logs.append("Robot returned to home position")

            # Checks to see if the Locked pose button is activated or not, and toggles the is_clicked3 state, which locks the robot's joints
            elif is_btn3:
                is_clicked3 = not is_clicked3
                yellow_button = WARNING if is_clicked3 else PANEL_BG
                if is_clicked3:
                    joint_angles[:5] = [40.0, 110.0, 150.0, 80.0, 90.0]
                    logs.append("Predefined pose activated")
                else:
                    joint_angles[:5] = [90.0, 90.0, 90.0, 90.0, 90.0]
                    logs.append("Predefined pose deactivated")

    # If not locked, read the joystick axes to control the robot's joints, 
    # and also check for D-pad input to control the claw angle
    angles = None
    if joysticks and not is_clicked3:
        joy = joysticks[0]
        n_axes = joy.get_numaxes()
        
        # Read the joystick axes with a deadzone to prevent small movements from affecting the robot's position, 
        # and convert these to angles for the robot's joints
        if n_axes > 4:
            raw_j1_lr = joy.get_axis(3) 
        if n_axes > 3:
            raw_j1_ud = joy.get_axis(2)
        if n_axes > 2:
            raw_j2_lr = joy.get_axis(1)
        if n_axes > 1:
            raw_j2_ud = joy.get_axis(0)
        else:
            raw_j1_lr = 0.0
            raw_j1_ud = 0.0
            raw_j2_lr = 0.0
            raw_j2_ud = 0.0

        # Convert the raw joystick axis values to angles for the robot's joints
        joint_angles[0] = axis_to_angle(raw_j1_lr)
        joint_angles[1] = axis_to_angle(-raw_j1_ud)
        joint_angles[2] = axis_to_angle(raw_j2_lr)
        joint_angles[3] = axis_to_angle(-raw_j2_ud)

        # Check for D-pad input to control the claw angle
        if joy.get_numhats() > 0:
            hat_x, hat_y = joy.get_hat(0)

            # The D-pad input is used to incrementally adjust the claw angle, allowing for fine control over the claw's position.
            # this was made before the claw was changed to a continuous rotation servo with a throttle, 
            # so it may not work as intended and needs to be reworked to control the claw's throttle instead of its angle
            if hat_x != 0:
                pass
            if hat_y == 1:
                claw_angle = joint_angles[5] + 1
                if claw_angle > 180:
                    claw_angle = 180
                elif claw_angle < 0:
                    claw_angle = 0
                joint_angles[5] = claw_angle
            elif hat_y == -1:
                claw_angle = joint_angles[5] - 1
                if claw_angle > 180:
                    claw_angle = 180
                elif claw_angle < 0:
                    claw_angle = 0
                joint_angles[5] = claw_angle
            
    # If the pose isn't locked and the robot has angles to read from the joystick, 
    # update the joint angles based on the inverse kinematics solver
    if angles is not None and not is_clicked3:
        try:
            # The angles returned by the IK solver may be in a nested structure, 
            # so we flatten it to get a simple list of angles for the joints
            flat = []
            for a in angles:
                if hasattr(a, "__iter__"):
                    flat.extend(np.array(a).flatten().tolist())
                else:
                    flat.append(a)
            flat = flat[:4]

            # set the joint angles based on the IK solver output, 
            # while keeping the claw angle unchanged, 
            # and also ensuring the angles are within the valid range for the robot's joints
            joint_angles = [
                round(np.degrees(flat[0])) % 360,
                round(np.degrees(flat[1])) % 360,
                round(np.degrees(flat[2])) % 360,
                round(np.degrees(flat[3])) % 360,
                joint_angles[4],
                joint_angles[5]
            ]

        except Exception as e:
            print("ANGLE ERROR:", e)
    
            
            
    # Drawing the DASHBOARD
    screen.fill(BACKGROUND)

    # adding the title to the top of the dashboard
    title_surf = font.render("C.O.R.I  DASHBOARD", True, ACCENT)
    screen.blit(title_surf, title_surf.get_rect(center=(width // 2, 40)))

    a, b, c, d = vector.solve_angles(joystick_vector[0], joystick_vector[1], joystick_vector[2])    
    angle_labels = ["A1", "A2", "A3", "A4", "A5"]
    
    # Looping through each of the 5 joint angles to draw the corresponding gauge on the dashboard, 
    # with the color of the gauge changing based on how far the angle deviates from 90 degrees to provide visual feedback on the joint's position
    # (THE COLOR CHANGING CODE WAS WRITTEN BY AI, BUT THE REST OF THE GAUGE CODE WAS WRITTEN BY ME)
    for i, (pos, angle) in enumerate(zip(circle_pos, joint_angles[:6])):
        deviation = abs(angle - 90.0) / 90.0  
        ring_r = int(80 + deviation * 175)
        ring_g = int(220 - deviation * 140)
        ring_b = int(150 - deviation * 150)
        ring_color = (ring_r, ring_g, ring_b)

        pygame.draw.circle(screen, GAUGE_BG,   pos, CIRCLE_R)
        pygame.draw.circle(screen, ring_color, pos, CIRCLE_R, CIRCLE_BORDER)

        needle_length = CIRCLE_R - 15
        angle_rad = math.radians(angle - 90)
        # Math used to calculate the end point of the needle based on the angle, 
        # with 0 degrees pointing straight up and increasing clockwise (Trigonometry YAY)
        end_x = pos[0] + needle_length * math.cos(angle_rad)
        end_y = pos[1] + needle_length * math.sin(angle_rad)
        pygame.draw.line(screen, ACCENT, pos, (int(end_x), int(end_y)), NEEDLE_WIDTH)

        
        pygame.draw.circle(screen, WHITE, pos, 4)

        label = font.render(f"{angle_labels[i]}: {int(angle)}°", True, TEXT_COLOR)
        screen.blit(label, label.get_rect(center=(pos[0], pos[1] + CIRCLE_R + 15)))

    
    # Draw the logs panel at the bottom of the dashboard, and loops through the last 7 logs to "scroll" the logs
    logs_rect = pygame.Rect(20, height - 180, width // 2 - 20, 150)
    draw_rounded_rect(screen, logs_rect, PANEL_BG, 10)
    draw_rounded_rect(screen, logs_rect, PANEL_BG, 10, 2)
    for i, line in enumerate(logs[-7:]):
        log_label = logs_font.render(line, True, TEXT_COLOR)
        screen.blit(log_label, (logs_rect.x + 10, logs_rect.y + 10 + i * 18))
    
    # Draw the backround panel for the buttons 
    panel_rect = pygame.Rect(width // 2 + 40, height - 150, 260, 110)
    draw_rounded_rect(screen, panel_rect, PANEL_BG, 15, 2)
    
    # set the buttons and their locations
    buttons = [
        (red_button,    "AI MODE", (width // 2 + 60,  height - 135)),
        (green_button,  "CLAW",    (width // 2 + 160, height - 135)),
        (blue_button,   "HOME",    (width // 2 + 60,  height - 90)),
        (yellow_button, "POSE",    (width // 2 + 160, height - 90)),
    ]
    # Drawing the buttons for AI mode, Claw activation, Home position, and locked pose on the dashboard, 
    # with their colors changing based on their active state to provide visual feedback to the user  
    for color, text, pos in buttons:
        btn_rect = pygame.Rect(pos[0], pos[1], 80, 35)
        draw_rounded_rect(screen, btn_rect, color, radius=5)
        lbl = small_font.render(text, True, WHITE)
        screen.blit(lbl, lbl.get_rect(center=btn_rect.center))


    # Sending the data through the websocket server to the raspberry pi, which then uses the pi_client.py to control the robot
    with ws_client.data_lock:
        ws_client.data["A1"] = joint_angles[0]
        ws_client.data["A2"] = joint_angles[1]
        ws_client.data["A3"] = joint_angles[2]
        ws_client.data["A4"] = joint_angles[3]
        ws_client.data["A5"] = joint_angles[4]
        ws_client.data["A6"] = scale_angle(joint_angles[5])
    
    print(scale_angle(joint_angles[5]))
    pygame.display.flip()
    
pygame.quit()
sys.exit()  

