import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pygame
import sys
import math
import numpy as np
from Robot_math import ik_solver
from error_handling import errors
from servers import ws_client
import threading

# Initialize websocket server background thread
threading.Thread(target=ws_client.start_server, daemon=True).start()
vector = ik_solver.IKSolver(L=1.0)

pygame.init()
pygame.joystick.init()

# Expanded height to accommodate the logging terminal safely
width, height = 700, 800
screen = pygame.display.set_mode((width, height))
clock = pygame.time.Clock()
pygame.display.set_caption("C.O.R.I DASHBOARD")

BACKGROUND = (18, 18, 30)
ACCENT_COLOR = (0, 200, 255)
PANEL_BG = (30, 30, 45)
TEXT_COLOR = (220, 220, 255)
WARNING = (255, 180, 50)
DANGER = (255, 80, 80)
SUCCESS = (80, 220, 150)
WHITE = (255, 255, 255)

CIRCLE_R = 70
CIRCLE_BORDER = 3
NEEDLE_WIDTH = 3
GAUGE_BG = (40, 40, 60)
NEEDLE_COLOR = ACCENT_COLOR

logs = ["System Initialized."]

font = pygame.font.SysFont('Arial', 20, bold=True)
small_font = pygame.font.SysFont('Arial', 14)
logs_font = pygame.font.SysFont('Consolas', 14)

# Global tracking array for 6 joints
joint_angles = [90.0, 90.0, 90.0, 90.0, 90.0, 90.0]

col_xs = [width // 4, width // 4 * 3]
row_ys = [120, 280, 440] # Spaced array layout for 6 gauges

circle_pos = []
for r in row_ys:
    for c in col_xs:
        circle_pos.append((c, r))

joysticks = []
for i in range(pygame.joystick.get_count()):
    joy = pygame.joystick.Joystick(i)
    joy.init()
    joysticks.append(joy)
    
red_button = PANEL_BG
green_button = PANEL_BG
blue_button = PANEL_BG
yellow_button = PANEL_BG

is_clicked_ai = False
is_clicked = False
is_clicked2 = False
is_clicked3 = False
running = True

def draw_rounded_rect(surface, rect, color, radius=10, border=0):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border > 0:
        pygame.draw.rect(surface, (255, 255, 255), rect, border, border_radius=radius)

while running:
    clock.tick(60) # Lock to 60 FPS to prevent processor choking
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.JOYBUTTONDOWN):
            x, y = pygame.mouse.get_pos() 
            
            # Interactive Control Bounds
            ai_mode_rect = pygame.Rect(width//2 - 90, height - 75, 80, 30)
            claw_rect = pygame.Rect(width//2 + 10, height - 75, 80, 30)
            home_rect = pygame.Rect(width//2 - 90, height - 35, 80, 30)
            pose_rect = pygame.Rect(width//2 + 10, height - 35, 80, 30)
            
            # Use mouse positioning click or register joystick button numbers
            is_button_0 = (event.type == pygame.JOYBUTTONDOWN and event.button == 0) or (event.type == pygame.MOUSEBUTTONDOWN and claw_rect.collidepoint(x, y))
            is_button_1 = (event.type == pygame.JOYBUTTONDOWN and event.button == 1) or (event.type == pygame.MOUSEBUTTONDOWN and ai_mode_rect.collidepoint(x, y))
            is_button_2 = (event.type == pygame.JOYBUTTONDOWN and event.button == 2) or (event.type == pygame.MOUSEBUTTONDOWN and home_rect.collidepoint(x, y))
            is_button_3 = (event.type == pygame.JOYBUTTONDOWN and event.button == 3) or (event.type == pygame.MOUSEBUTTONDOWN and pose_rect.collidepoint(x, y))

            if is_button_0:
                is_clicked = not is_clicked
                logs.append("Claw Activated" if is_clicked else "Claw Deactivated")
                green_button = SUCCESS if is_clicked else PANEL_BG
                joint_angles[4] = 40.0 if is_clicked else 180.0
                
            elif is_button_1:
                is_clicked_ai = not is_clicked_ai
                logs.append("AI Mode " + ("Activated" if is_clicked_ai else "Deactivated"))
                red_button = DANGER if is_clicked_ai else PANEL_BG
                
            elif is_button_2:
                logs.append("Robot returned to home position")
                blue_button = ACCENT_COLOR if not is_clicked2 else PANEL_BG
                is_clicked2 = not is_clicked2
                joint_angles = [90.0, 90.0, 90.0, 90.0, joint_angles[4], joint_angles[5]]
                
            elif is_button_3:
                is_clicked3 = not is_clicked3
                logs.append("Predefined pose activated" if is_clicked3 else "Predefined pose deactivated")
                yellow_button = WARNING if is_clicked3 else PANEL_BG
                if is_clicked3:
                    joint_angles = [40.0, 110.0, 150.0, 80.0, joint_angles[4], joint_angles[5]]
                else:
                    joint_angles = [90.0, 90.0, 90.0, 90.0, joint_angles[4], joint_angles[5]]

    # Process Joystick Coordinate Inputs
    if joysticks and not is_clicked3:
        joystick = joysticks[0]
        number_of_axes = joystick.get_numaxes()
        
        raw_ax0 = joystick.get_axis(0) if number_of_axes > 0 else 0.0
        raw_ax1 = joystick.get_axis(1) if number_of_axes > 1 else 0.0
        raw_z   = joystick.get_axis(3) if number_of_axes > 3 else (joystick.get_axis(2) if number_of_axes > 2 else 0.0)
        
        DEADZONE = 0.12       
        SENSITIVITY_MULT = 1.5 
        
        def apply_sensitivity(axis_value):
            if abs(axis_value) < DEADZONE:
                return 0.0
            sign = np.sign(axis_value)
            scaled_val = (abs(axis_value) - DEADZONE) / (1.0 - DEADZONE)
            return (scaled_val ** 3) * sign * SENSITIVITY_MULT

        ax0 = apply_sensitivity(raw_ax0)
        ax1 = apply_sensitivity(raw_ax1)
        z   = apply_sensitivity(raw_z)
        
        try:
            # Only update if vectors are actively out of deadzone bounds
            if ax0 != 0.0 or ax1 != 0.0 or z != 0.0:
                angles = vector.update_from_vector(ax0, -ax1, z)
                if angles is not None:
                    flat = []
                    for item in angles:
                        if hasattr(item, "__iter__"):
                            flat.extend(np.array(item).flatten().tolist())
                        else:
                            flat.append(item)
                    
                    # Map calculation updates directly across your base target angles
                    joint_angles[0] = round(np.degrees(flat[0])) % 360
                    joint_angles[1] = round(np.degrees(flat[1])) % 360
                    joint_angles[2] = round(np.degrees(flat[2])) % 360
                    joint_angles[3] = round(np.degrees(flat[3])) % 360
        except Exception as e:
            if str(e) not in logs:
                logs.append(str(e))
                
    # --- Rendering Pipeline ---
    screen.fill(BACKGROUND)
    
    # Render Dial Gauges
    for i, (pos, angle) in enumerate(zip(circle_pos, joint_angles)):
        pygame.draw.circle(screen, GAUGE_BG, pos, CIRCLE_R)
        pygame.draw.circle(screen, TEXT_COLOR, pos, CIRCLE_R, CIRCLE_BORDER)
        
        needle_length = CIRCLE_R - 15
        angle_rad = math.radians(angle - 90)
        end_x = pos[0] + needle_length * math.cos(angle_rad)
        end_y = pos[1] + needle_length * math.sin(angle_rad)
        
        pygame.draw.line(screen, NEEDLE_COLOR, pos, (int(end_x), int(end_y)), NEEDLE_WIDTH)
        
        label = font.render(f"A{i+1}: {int(angle)}°", True, TEXT_COLOR)
        label_rect = label.get_rect(center=(pos[0], pos[1] + CIRCLE_R + 15))
        screen.blit(label, label_rect)

    # Render Log Terminal (Repositioned safely to the left column space)
    logs_rect = pygame.Rect(20, height - 180, width // 2 - 20, 150)
    draw_rounded_rect(screen, logs_rect, PANEL_BG, 10)
    logs_to_show = logs[-7:] # Only show last 7 lines to prevent text overflowing bounds
    
    for i, line in enumerate(logs_to_show):
        log_label = logs_font.render(line, True, TEXT_COLOR)
        screen.blit(log_label, (logs_rect.x + 10, logs_rect.y + 10 + i * 18))
    
    # Render Right Control Interaction Box Panel
    panel_rect = pygame.Rect(width//2 + 40, height - 150, 260, 110)
    draw_rounded_rect(screen, panel_rect, PANEL_BG, 15, 2)
    
    buttons = [
        (red_button, "AI MODE", (width//2 + 60, height - 135)),
        (green_button, "CLAW", (width//2 + 160, height - 135)),
        (blue_button, "HOME", (width//2 + 60, height - 90)),
        (yellow_button, "POSE", (width//2 + 160, height - 90))
    ]
    
    for color, text, pos in buttons:
        button_rect = pygame.Rect(pos[0], pos[1], 80, 35)
        draw_rounded_rect(screen, button_rect, color, radius=5)
        label = small_font.render(text, True, WHITE)
        label_rect = label.get_rect(center=button_rect.center)
        screen.blit(label, label_rect)
    
    # Send verified dataset payload to Websocket Loop Context
    with ws_client.data_lock:
        ws_client.data["A1"] = joint_angles[0]
        ws_client.data["A2"] = joint_angles[1]
        ws_client.data["A3"] = joint_angles[2]
        ws_client.data["A4"] = joint_angles[3]
        ws_client.data["A5"] = joint_angles[4]
        ws_client.data["A6"] = joint_angles[5]
    
    pygame.display.flip()
    
pygame.quit()
sys.exit()