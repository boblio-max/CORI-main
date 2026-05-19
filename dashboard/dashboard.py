import sys, os
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

vector = ik_solver.IKSolver(L=1.0)

pygame.init()
pygame.joystick.init()

width, height = 700, 700
screen = pygame.display.set_mode((width, height))
clock = pygame.time.Clock()
pygame.display.set_caption("C.O.R.I DASHBOARD")

L = 1.0
A1 = 0
A2 = 0
A3 = 0
A4 = 0
x = 0.5  

BACKGROUND = (18, 18, 30)
ACCENT_COLOR = (0, 200, 255)
SECONDARY_ACCENT = (100, 255, 200)
PANEL_BG = (30, 30, 45)
TEXT_COLOR = (220, 220, 255)
WARNING = (255, 180, 50)
DANGER = (255, 80, 80)
SUCCESS = (80, 220, 150)

CIRCLE_R = 70
CIRCLE_BORDER = 3
NEEDLE_WIDTH = 3
GAUGE_BG = (40, 40, 60)
NEEDLE_COLOR = ACCENT_COLOR

logs = []

font = pygame.font.SysFont('Arial', 20, bold=True)
small_font = pygame.font.SysFont('Arial', 14)
logs_font = pygame.font.SysFont('Consolas', 15)


joint_angles = [180.0, 180.0, 90.0, 90.0, 0.0, 0.0]

col_xs = [width // 6, width // 2.5]
row_ys = [height // 12 + 40, height // 2 - 120]

circle_pos = []

for i in range(2):
    for j in range(2):
        circle_pos.append((col_xs[i], row_ys[j]))


joysticks = []
for i in range(pygame.joystick.get_count()):
    joy = pygame.joystick.Joystick(i)
    joy.init()
    joysticks.append(joy)
    
red_button = PANEL_BG
green_button = PANEL_BG
blue_button = PANEL_BG
yellow_button = PANEL_BG
WHITE = (255, 255, 255)

is_clicked_ai = False
is_clicked = False
is_clicked1 = False
is_clicked2 = False
is_clicked3 = False
running = True

def draw_rounded_rect(surface, rect, color, radius=10, border=0):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border > 0:
        pygame.draw.rect(surface, (255, 255, 255), rect, border, border_radius=radius)
        
def normalize_angle(angle):
    return (x % 360 + 360) % 360

def clamp(angle):
    return max(0, min(180, angle))

while running:
    joystick_vector = (0.0, 0.0, 0.0)
    
    a,b,c,d = vector.solve_angles(joystick_vector[0], joystick_vector[1], joystick_vector[2])
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.JOYBUTTONDOWN:
            
            x, y = pygame.mouse.get_pos() 
            ai_mode_rect = pygame.Rect(width//2 - 90, height - 75, 80, 30)
            claw_rect = pygame.Rect(width//2 + 10, height - 75, 80, 30)
            home_rect = pygame.Rect(width//2 - 90, height - 35, 80, 30)
            pose_rect = pygame.Rect(width//2 + 10, height - 35, 80, 30)
            
            try:
                if event.button == 0 or claw_rect.collidepoint(x, y):
                    is_clicked = not is_clicked
                    logs.append("Claw Activated" if is_clicked else "Claw Deactivated")
                    green_button = SUCCESS if is_clicked else PANEL_BG
                    joint_angles[0] = 40.0 if is_clicked else 180.0
                    
                elif event.button == 1 or ai_mode_rect.collidepoint(x, y):
                    is_clicked_ai = not is_clicked_ai
                    logs.append("AI Mode " + ("Activated" if is_clicked_ai else "Deactivated"))
                    red_button = DANGER if is_clicked_ai else PANEL_BG
                    
                elif event.button == 2 or home_rect.collidepoint(x, y):
                    logs.append("Robot returned to original location")
                    blue_button = ACCENT_COLOR if not is_clicked2 else PANEL_BG
                    is_clicked2 = not is_clicked2
                    
                elif event.button == 3 or pose_rect.collidepoint(x, y):
                    logs.append("Predefined pose activated" if not is_clicked3 else "Predefined pose deactivated")
                    yellow_button = WARNING if not is_clicked3 else PANEL_BG
                    is_clicked3 = not is_clicked3
                    joint_angles = [40.0, 110.0, 150.0, 80.0, 0.0, 0.0] if is_clicked3 else [180.0, 180.0, 90.0, 90.0, 0.0, 0.0]

            except Exception:
                pass
        
        angles = None
        if joysticks:
            joystick = joysticks[0]
            number_of_axes = joystick.get_numaxes()
            ax0 = joystick.get_axis(0) if number_of_axes > 0 else 0.0
            ax1 = joystick.get_axis(1) if number_of_axes > 1 else 0.0
            z = joystick.get_axis(3) if number_of_axes > 3 else (joystick.get_axis(2) if number_of_axes > 2 else 0.0)
            vector_to_pass = [ax0 * 3.0, -ax1 * 3.0, z * 3.0]
            
            try:
                n = f"{ax0} {ax1} {z}"
                angles = ik_solver.IKSolver().update_from_vector(vector_to_pass[0], vector_to_pass[1], vector_to_pass[2])
            except Exception as e:
                logs.append(str(e))
                
        if angles and not is_clicked3:
            try:
                a1 = float(angles.get("A1", joint_angles[0]))
                a2 = float(angles.get("A2", joint_angles[1]))
                a3 = float(angles.get("A3", joint_angles[2]))
                a4 = float(angles.get("A4", joint_angles[3]))
            except Exception:
                a1, a2, a3, a4, un, un1 = joint_angles
            
            joint_angles = [
                round(normalize_angle(a1)),
                round(normalize_angle(a2)),
                round(normalize_angle(a3)),
                round(normalize_angle(a4)),
                joint_angles[4],
                joint_angles[5]
            ]
            
            
            
    screen.fill(BACKGROUND)
    a, b, c, d = vector.solve_angles(joystick_vector[0], joystick_vector[1], joystick_vector[2])
    
    draw_rounded_rect(screen, (width//2 - 100, height - 80, 200, 70), PANEL_BG, radius=2)
    
    for i, (pos, angle) in enumerate(zip(circle_pos, joint_angles)):
        pygame.draw.circle(screen, GAUGE_BG, pos, CIRCLE_R)
        pygame.draw.circle(screen, TEXT_COLOR, pos, CIRCLE_R, CIRCLE_BORDER)
        
        needle_length = CIRCLE_R - 15
        angle_rad = math.radians(angle - 90)
        end_x = pos[0] + needle_length * math.cos(angle_rad)
        end_y = pos[1] + needle_length * math.sin(angle_rad)
        
        pygame.draw.line(screen, NEEDLE_COLOR, pos, (end_x, end_y), NEEDLE_WIDTH)
        
        label = font.render(f"A{i+1}", True, TEXT_COLOR)
        label_rect = label.get_rect(center=(pos[0], pos[1] + CIRCLE_R + 20))
        screen.blit(label, label_rect)

    
    panel_rect = pygame.Rect(width//2 - 120, height - 100, 240, 80)
    draw_rounded_rect(screen, panel_rect, PANEL_BG, 15, 2)
    
    buttons = [
        (red_button, "AI MODE", (width//2 - 90, height - 75)),
        (green_button, "CLAW", (width//2 + 10, height - 75)),
        (blue_button, "HOME", (width//2 - 90, height - 35)),
        (yellow_button, "POSE", (width//2 + 10, height - 35))
    ]
    
    for color, text, pos in buttons:
        button_rect = pygame.Rect(pos[0], pos[1], 80, 30)
        draw_rounded_rect(screen, button_rect, color, radius=5)
        label = small_font.render(text, True, WHITE)
        label_rect = label.get_rect(center=button_rect.center)
        screen.blit(label, label_rect)
    
    logs_rect = pygame.Rect(10, height - 150, width - 20, 40)
    draw_rounded_rect(screen, logs_rect, PANEL_BG, 10)
    logs_to_show = logs[-15:]
    
    for i, line in enumerate(logs_to_show):
        log_label = logs_font.render(line, True, TEXT_COLOR)
        screen.blit(log_label, (logs_rect.x + 10, logs_rect.y + 5 + i * 18))
    
    pygame.display.flip()
    
pygame.quit()
sys.exit()  