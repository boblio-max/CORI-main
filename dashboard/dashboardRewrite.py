import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pygame
import sys
import math
import numpy as np
from servers import ws_client
import threading

# Initialize websocket server background thread
threading.Thread(target=ws_client.start_server, daemon=True).start()

pygame.init()
pygame.joystick.init()

# Window dimensions
width, height = 700, 800
screen = pygame.display.set_mode((width, height))
clock = pygame.time.Clock()
pygame.display.set_caption("C.O.R.I DASHBOARD")

# --- Color Palette ---
BACKGROUND  = (18, 18, 30)
ACCENT      = (0, 200, 255)
PANEL_BG    = (30, 30, 45)
TEXT_COLOR  = (220, 220, 255)
WARNING     = (255, 180, 50)
DANGER      = (255, 80, 80)
SUCCESS     = (80, 220, 150)
WHITE       = (255, 255, 255)
DIM         = (100, 100, 130)

# --- Gauge Settings ---
CIRCLE_R      = 70
CIRCLE_BORDER = 3
NEEDLE_WIDTH  = 3
GAUGE_BG      = (40, 40, 60)

# --- Fonts ---
font       = pygame.font.SysFont('Arial', 20, bold=True)
small_font = pygame.font.SysFont('Arial', 14)
logs_font  = pygame.font.SysFont('Consolas', 14)

# --- State ---
# joint_angles[0..4] = A1..A5  (index 5 unused / reserved)
joint_angles = [90.0, 90.0, 90.0, 90.0, 90.0, 90.0]
logs = ["System Initialized."]

red_button    = PANEL_BG
green_button  = PANEL_BG
blue_button   = PANEL_BG
yellow_button = PANEL_BG

is_clicked_ai = False
is_clicked    = False   # claw
is_clicked2   = False   # home
is_clicked3   = False   # pose

# D-Pad angle 5 incremental step (degrees per frame while held)
DPAD_STEP = 1.5

# Joystick deadzone and mapping constants
DEADZONE = 0.10   # Ignore tiny axis drift

# Gauge grid layout  (5 gauges: 2 columns, rows 1/2 have 2 each, row 3 has 1 centered)
col_xs      = [width // 4, width // 4 * 3]
row_ys      = [120, 280, 440]
circle_pos  = [
    (col_xs[0], row_ys[0]),  # A1
    (col_xs[1], row_ys[0]),  # A2
    (col_xs[0], row_ys[1]),  # A3
    (col_xs[1], row_ys[1]),  # A4
    (width // 2, row_ys[2]), # A5 — centered on its own row
]

# --- Joystick init ---
joysticks = []
for i in range(pygame.joystick.get_count()):
    joy = pygame.joystick.Joystick(i)
    joy.init()
    joysticks.append(joy)
    logs.append(f"Joystick connected: {joy.get_name()}")

running = True

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def draw_rounded_rect(surface, rect, color, radius=10, border=0):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border > 0:
        pygame.draw.rect(surface, WHITE, rect, border, border_radius=radius)


def axis_to_angle(raw_axis):
    """
    Map a joystick axis value [-1, 1] to an angle [0°, 180°].
    Center (0.0) → 90°.  Full left/down (-1.0) → 0°.  Full right/up (+1.0) → 180°.
    Applies deadzone: values inside [-DEADZONE, +DEADZONE] snap to 0.0 (→ 90°).
    """
    if abs(raw_axis) < DEADZONE:
        raw_axis = 0.0
    else:
        # Re-scale so the dead zone boundary maps cleanly to 0
        sign = 1 if raw_axis > 0 else -1
        raw_axis = sign * (abs(raw_axis) - DEADZONE) / (1.0 - DEADZONE)
    # axis ∈ [-1, 1]  →  angle ∈ [0, 180]
    return 90.0 + raw_axis * 90.0


def clamp(value, lo, hi):
    return max(lo, min(hi, value))

# ---------------------------------------------------------------------------
# Main Loop
# ---------------------------------------------------------------------------
while running:
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.JOYDEVICEADDED:
            joy = pygame.joystick.Joystick(event.device_index)
            joy.init()
            joysticks.append(joy)
            logs.append(f"Joystick connected: {joy.get_name()}")

        elif event.type == pygame.JOYDEVICEREMOVED:
            joysticks = [j for j in joysticks if j.get_instance_id() != event.instance_id]
            logs.append("Joystick disconnected.")

        elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.JOYBUTTONDOWN):
            mx, my = pygame.mouse.get_pos()

            # Button rects
            ai_mode_rect = pygame.Rect(width // 2 - 90, height - 75, 80, 30)
            claw_rect    = pygame.Rect(width // 2 + 10, height - 75, 80, 30)
            home_rect    = pygame.Rect(width // 2 - 90, height - 35, 80, 30)
            pose_rect    = pygame.Rect(width // 2 + 10, height - 35, 80, 30)

            is_btn0 = (event.type == pygame.JOYBUTTONDOWN and event.button == 0) or \
                      (event.type == pygame.MOUSEBUTTONDOWN and claw_rect.collidepoint(mx, my))
            is_btn1 = (event.type == pygame.JOYBUTTONDOWN and event.button == 1) or \
                      (event.type == pygame.MOUSEBUTTONDOWN and ai_mode_rect.collidepoint(mx, my))
            is_btn2 = (event.type == pygame.JOYBUTTONDOWN and event.button == 2) or \
                      (event.type == pygame.MOUSEBUTTONDOWN and home_rect.collidepoint(mx, my))
            is_btn3 = (event.type == pygame.JOYBUTTONDOWN and event.button == 3) or \
                      (event.type == pygame.MOUSEBUTTONDOWN and pose_rect.collidepoint(mx, my))

            if is_btn0:
                is_clicked = not is_clicked
                logs.append("Claw Activated" if is_clicked else "Claw Deactivated")
                green_button = SUCCESS if is_clicked else PANEL_BG

            elif is_btn1:
                is_clicked_ai = not is_clicked_ai
                logs.append("AI Mode " + ("Activated" if is_clicked_ai else "Deactivated"))
                red_button = DANGER if is_clicked_ai else PANEL_BG

            elif is_btn2:
                is_clicked2 = not is_clicked2
                blue_button = ACCENT if is_clicked2 else PANEL_BG
                joint_angles[:5] = [90.0, 90.0, 90.0, 90.0, 90.0]
                logs.append("Robot returned to home position")

            elif is_btn3:
                is_clicked3 = not is_clicked3
                yellow_button = WARNING if is_clicked3 else PANEL_BG
                if is_clicked3:
                    joint_angles[:5] = [40.0, 110.0, 150.0, 80.0, 90.0]
                    logs.append("Predefined pose activated")
                else:
                    joint_angles[:5] = [90.0, 90.0, 90.0, 90.0, 90.0]
                    logs.append("Predefined pose deactivated")


    if joysticks and not is_clicked3:
        joy = joysticks[0]
        n_axes = joy.get_numaxes()

        raw_j1_lr = joy.get_axis(0) if n_axes > 0 else 0.0
        raw_j1_ud = joy.get_axis(1) if n_axes > 1 else 0.0
        raw_j2_lr = joy.get_axis(2) if n_axes > 2 else 0.0
        raw_j2_ud = joy.get_axis(3) if n_axes > 3 else 0.0

        # Angle 1: J1 left/right
        joint_angles[0] = axis_to_angle(raw_j1_lr)

        # Angle 2: J1 up/down  (invert so pushing up = higher angle)
        joint_angles[1] = axis_to_angle(-raw_j1_ud)

        # Angle 3: J2 left/right
        joint_angles[2] = axis_to_angle(raw_j2_lr)

        # Angle 4: J2 up/down  (invert so pushing up = higher angle)
        joint_angles[3] = axis_to_angle(-raw_j2_ud)

        # Angle 5: D-Pad left/right (incremental)
        if joy.get_numhats() > 0:
            hat_x, _hat_y = joy.get_hat(0)
            joint_angles[4] = clamp(joint_angles[4] + hat_x * DPAD_STEP, 0.0, 180.0)

    # -----------------------------------------------------------------------
    # Rendering
    # -----------------------------------------------------------------------
    screen.fill(BACKGROUND)

    # Title
    title_surf = font.render("C.O.R.I  DASHBOARD", True, ACCENT)
    screen.blit(title_surf, title_surf.get_rect(center=(width // 2, 40)))

    # Joystick legend
    legend_lines = [
        "J1 ←→ : A1   J1 ↑↓ : A2",
        "J2 ←→ : A3   J2 ↑↓ : A4",
        "D-Pad ←→ : A5  (center = 90°)",
    ]
    for li, line in enumerate(legend_lines):
        surf = small_font.render(line, True, DIM)
        screen.blit(surf, surf.get_rect(center=(width // 2, 68 + li * 18)))

    # Dial Gauges (5 gauges for A1–A5)
    angle_labels = ["A1", "A2", "A3", "A4", "A5"]
    for i, (pos, angle) in enumerate(zip(circle_pos, joint_angles[:5])):
        # Glow ring — colour shifts from green (90°) toward red at extremes
        deviation = abs(angle - 90.0) / 90.0  # 0 = center, 1 = extreme
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

        # Centre dot
        pygame.draw.circle(screen, WHITE, pos, 4)

        label = font.render(f"{angle_labels[i]}: {int(angle)}°", True, TEXT_COLOR)
        screen.blit(label, label.get_rect(center=(pos[0], pos[1] + CIRCLE_R + 15)))

    # Log Terminal
    logs_rect = pygame.Rect(20, height - 180, width // 2 - 20, 150)
    draw_rounded_rect(screen, logs_rect, PANEL_BG, 10)
    for i, line in enumerate(logs[-7:]):
        log_label = logs_font.render(line, True, TEXT_COLOR)
        screen.blit(log_label, (logs_rect.x + 10, logs_rect.y + 10 + i * 18))

    # Control Button Panel
    panel_rect = pygame.Rect(width // 2 + 40, height - 150, 260, 110)
    draw_rounded_rect(screen, panel_rect, PANEL_BG, 15, 2)

    buttons = [
        (red_button,    "AI MODE", (width // 2 + 60,  height - 135)),
        (green_button,  "CLAW",    (width // 2 + 160, height - 135)),
        (blue_button,   "HOME",    (width // 2 + 60,  height - 90)),
        (yellow_button, "POSE",    (width // 2 + 160, height - 90)),
    ]
    for color, text, pos in buttons:
        btn_rect = pygame.Rect(pos[0], pos[1], 80, 35)
        draw_rounded_rect(screen, btn_rect, color, radius=5)
        lbl = small_font.render(text, True, WHITE)
        screen.blit(lbl, lbl.get_rect(center=btn_rect.center))

    # Websocket payload
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