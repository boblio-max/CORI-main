# Import necessary modules and set up paths
import sys, os
# Add parent directory to sys.path for module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pygame
import sys
import math
import numpy as np
from servers import ws_client
import threading

# Start the WebSocket server in a separate thread
# Initialize websocket server background thread
threading.Thread(target=ws_client.start_server, daemon=True).start()

# Init pygame and joystick
pygame.init()
pygame.joystick.init()

# Window dimensions
width, height = 700, 800
screen = pygame.display.set_mode((width, height))
clock = pygame.time.Clock()
pygame.display.set_caption("C.O.R.I DASHBOARD")

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

# Initialized fonts for rendering text on the dashboard
font       = pygame.font.SysFont('Arial', 20, bold=True)
small_font = pygame.font.SysFont('Arial', 14)
logs_font  = pygame.font.SysFont('Consolas', 14)

# Initialize joint angles 
joint_angles = [90.0, 90.0, 90.0, 90.0, 90.0, 0.0]
logs = ["System Initialized."]

red_button    = PANEL_BG
green_button  = PANEL_BG
blue_button   = PANEL_BG
yellow_button = PANEL_BG

is_clicked_ai = False
is_clicked    = False   
is_clicked2   = False   
is_clicked3   = False 

DPAD_STEP = 1.5
DEADZONE = 0.10  

# Define positions for the gauges on the dashboard
col_xs      = [width // 4, width // 4 * 3]
row_ys      = [120, 280, 440]
circle_pos  = [
    (col_xs[0], row_ys[0]),  
    (col_xs[1], row_ys[0]),  
    (col_xs[0], row_ys[1]),  
    (col_xs[1], row_ys[1]),  
    (width // 2, row_ys[2]), 
]

# Gets the joysticks initialized 
joysticks = []
for i in range(pygame.joystick.get_count()):
    joy = pygame.joystick.Joystick(i)
    joy.init()
    joysticks.append(joy)
    logs.append(f"Joystick connected: {joy.get_name()}")

running = True

# Helper function to draw the rounded rectangles for the buttons and panels
def draw_rounded_rect(surface, rect, color, radius=10, border=0):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border > 0:
        pygame.draw.rect(surface, WHITE, rect, border, border_radius=radius)

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
def clamp(value, lo, hi):
    return max(lo, min(hi, value))

# Main loop  
while running:
    # limit the framerate to 60 FPS
    clock.tick(60)

    # Check for events such as joystick connections, button presses, and window closing
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Handle joystick connection and disconnection events to update the list of active joysticks and log these events
        elif event.type == pygame.JOYDEVICEADDED:
            joy = pygame.joystick.Joystick(event.device_index)
            joy.init()
            joysticks.append(joy)
            logs.append(f"Joystick connected: {joy.get_name()}")

        elif event.type == pygame.JOYDEVICEREMOVED:
            joysticks = [j for j in joysticks if j.get_instance_id() != event.instance_id]
            logs.append("Joystick disconnected.")

        # Handle button presses from both the joystick and mouse clicks on the dashboard buttons, updating the state of the buttons and logging these actions
        elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.JOYBUTTONDOWN):
            mx, my = pygame.mouse.get_pos()

            # Button rects
            ai_mode_rect = pygame.Rect(width // 2 - 90, height - 75, 80, 30)
            claw_rect    = pygame.Rect(width // 2 + 10, height - 75, 80, 30)
            home_rect    = pygame.Rect(width // 2 - 90, height - 35, 80, 30)
            pose_rect    = pygame.Rect(width // 2 + 10, height - 35, 80, 30)

            # Different buttons can be triggered by either a joystick button press or a mouse click on the corresponding area of the dashboard, allowing for flexible control options
            is_btn0 = (event.type == pygame.JOYBUTTONDOWN and event.button == 0) or \
                      (event.type == pygame.MOUSEBUTTONDOWN and claw_rect.collidepoint(mx, my))
            is_btn1 = (event.type == pygame.JOYBUTTONDOWN and event.button == 1) or \
                      (event.type == pygame.MOUSEBUTTONDOWN and ai_mode_rect.collidepoint(mx, my))
            is_btn2 = (event.type == pygame.JOYBUTTONDOWN and event.button == 2) or \
                      (event.type == pygame.MOUSEBUTTONDOWN and home_rect.collidepoint(mx, my))
            is_btn3 = (event.type == pygame.JOYBUTTONDOWN and event.button == 3) or \
                      (event.type == pygame.MOUSEBUTTONDOWN and pose_rect.collidepoint(mx, my))

            # Checks to see if the claw is activated or not, and toggles the is_clicked state
            if is_btn0:
                is_clicked = not is_clicked
                logs.append("Claw Activated" if is_clicked else "Claw Deactivated")
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
                    joint_angles[:5] = joint_angles[:5]  # Keep current angles but prevent changes
                    logs.append("Locked pose activated")
                else:
                    joint_angles[:5] = joint_angles[:5]  # Allow changes again
                    logs.append("Locked pose deactivated")

    # 
    if joysticks and not is_clicked3:
        joy = joysticks[0]
        n_axes = joy.get_numaxes()

        raw_j1_lr = joy.get_axis(0) if n_axes > 0 else 0.0
        raw_j1_ud = joy.get_axis(1) if n_axes > 1 else 0.0
        raw_j2_lr = joy.get_axis(2) if n_axes > 2 else 0.0
        raw_j2_ud = joy.get_axis(3) if n_axes > 3 else 0.0

        joint_angles[0] = axis_to_angle(raw_j1_lr)
        joint_angles[1] = axis_to_angle(-raw_j1_ud)
        joint_angles[2] = axis_to_angle(raw_j2_lr)
        joint_angles[3] = axis_to_angle(-raw_j2_ud)
        if joy.get_numhats() > 0:
            hat_x, _hat_y = joy.get_hat(0)
            joint_angles[4] = clamp(joint_angles[4] + hat_x * DPAD_STEP, 0.0, 180.0)

    # Drawing the DASHBOARD
    screen.fill(BACKGROUND)

    # adding the title to the top of the dashboard
    title_surf = font.render("C.O.R.I  DASHBOARD", True, ACCENT)
    screen.blit(title_surf, title_surf.get_rect(center=(width // 2, 40)))

    # Looping through each of the 5 joint angles to draw the corresponding gauge on the dashboard, 
    # with the color of the gauge changing based on how far the angle deviates from 90 degrees to provide visual feedback on the joint's position
    # (THE COLOR CHANGING CODE WAS WRITTEN BY AI, BUT THE REST OF THE GAUGE CODE WAS WRITTEN BY ME)
    angle_labels = ["A1", "A2", "A3", "A4", "A5"]
    for i, (pos, angle) in enumerate(zip(circle_pos, joint_angles[:5])):
        deviation = abs(angle - 90.0) / 90.0 
        ring_r = int(80 + deviation * 175)
        ring_g = int(220 - deviation * 140)
        ring_b = int(150 - deviation * 150)
        ring_color = (ring_r, ring_g, ring_b)

        pygame.draw.circle(screen, GAUGE_BG,   pos, CIRCLE_R)
        pygame.draw.circle(screen, ring_color, pos, CIRCLE_R, CIRCLE_BORDER)

        needle_length = CIRCLE_R - 15
        angle_rad = math.radians(angle - 90)
        end_x = pos[0] + needle_length * math.cos(angle_rad)
        end_y = pos[1] + needle_length * math.sin(angle_rad)
        pygame.draw.line(screen, ACCENT, pos, (int(end_x), int(end_y)), NEEDLE_WIDTH)
        pygame.draw.circle(screen, WHITE, pos, 4)

        label = font.render(f"{angle_labels[i]}: {int(angle)}°", True, TEXT_COLOR)
        screen.blit(label, label.get_rect(center=(pos[0], pos[1] + CIRCLE_R + 15)))

    # Draw the logs panel at the bottom of the dashboard, and loops through the last 7 logs to "scroll" the logs
    logs_rect = pygame.Rect(20, height - 180, width // 2 - 20, 150)
    draw_rounded_rect(screen, logs_rect, PANEL_BG, 10)
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
        (yellow_button, "LOCK",    (width // 2 + 160, height - 90)),
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
        ws_client.data["A6"] = joint_angles[5]

    pygame.display.flip()

#Quit
pygame.quit()
sys.exit()