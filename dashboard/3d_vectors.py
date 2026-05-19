import pygame
import numpy as np
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Robot_math import ik_solver

vector = ik_solver.IKSolver(L=1.0)

pygame.init()
pygame.joystick.init()

width, height = 800, 600

screen = pygame.display.set_mode((width, height))
clock = pygame.time.Clock()
pygame.display.set_caption("3D Vector Visualization")

joysticks = []
for i in range(pygame.joystick.get_count()):
    joy = pygame.joystick.Joystick(i)
    joy.init()
    joysticks.append(joy)
    
angle_x, angle_y = 0, 0
x_val, y_val, z_val = 0, 0, 0

L = 1
Lm = 1.57079
A1 = 0
A2 = 0
A3 = 0
A4 = 0
x = 0.5  
x_val, y_val, z_val = 0.5, 0.5, 0.5
n = (x_val, y_val, z_val)

# Made with AI
def project(vector, angle_x, angle_y):
    ry = np.array([
        [np.cos(angle_y), 0, np.sin(angle_y)],
        [0, 1, 0],
        [-np.sin(angle_y), 0, np.cos(angle_y)]
    ])
    
    rx = np.array([
        [1, 0, 0],
        [0, np.cos(angle_x), -np.sin(angle_x)],
        [0, np.sin(angle_x), np.cos(angle_x)]
    ])
    
    rotated = rx @ (ry @ vector)
    return int(rotated[0] + width/2), int(rotated[1] + height/2)

scale = 1.0
is_shown = True
reset = False

running = True
while running:
    dt = clock.tick(60) / 1000.0
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
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
            pass
        
    x_val = x_val
    
    n = (x_val * 30, y_val * 30, z_val * 30)
    
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:  
        angle_y -= 2 * dt
    if keys[pygame.K_RIGHT]: 
        angle_y += 2 * dt
    if keys[pygame.K_UP]:    
        angle_x -= 2 * dt
    if keys[pygame.K_DOWN]: 
        angle_x += 2 * dt
    
    
    if keys[pygame.K_PAGEUP]:
        scale += 0.1
    if keys[pygame.K_PAGEDOWN]:
        if scale > 0.0:
            scale -= 0.1
        else:
            scale = 0
            
    
    if keys[pygame.K_r]:
        scale = 1.0
        angle_x, angle_y = 0, 0
    
    if keys[pygame.K_s]:
        reset = not reset
    
    if keys[pygame.K_x]:
        angle_x, angle_y = 1.63, 1.57
    if keys[pygame.K_y]:
        angle_x, angle_y = 0.03, 0
    if keys[pygame.K_z]:
        angle_x, angle_y = 1.56, 0

    a, b, c = vector.update_from_vector(n[0], n[1], n[2])
    
    vectors = [
            {'color': (255, 0, 0), 'vec': np.array([100 * scale, 0, 0])},   # X (Red)
            {'color': (0, 255, 0), 'vec': np.array([0, 100 * scale, 0])},   # Y (Green)
            {'color': (0, 0, 255), 'vec': np.array([0, 0, 100 * scale])},   # Z (Blue)
            {'color': (255, 0, 0), 'vec': np.array([-100 * scale, 0, 0])},  # X (Red)
            {'color': (0, 255, 0), 'vec': np.array([0, -100 * scale, 0])},  # Y (Green)
            {'color': (0, 0, 255), 'vec': np.array([0, 0, -100 * scale])},   # Z (Blue)
            {'color': (255, 255, 255), 'vec': np.array([x_val* 40 * scale, y_val * 40 * scale, z_val * 40 * scale])}
        ]
    if is_shown:
        vectors = [
            {'color': (255, 0, 0), 'vec': np.array([100 * scale, 0, 0])},   # X (Red)
            {'color': (0, 255, 0), 'vec': np.array([0, 100 * scale, 0])},   # Y (Green)
            {'color': (0, 0, 255), 'vec': np.array([0, 0, 100 * scale])},   # Z (Blue)
            {'color': (255, 0, 0), 'vec': np.array([-100 * scale, 0, 0])},  # X (Red)
            {'color': (0, 255, 0), 'vec': np.array([0, -100 * scale, 0])},  # Y (Green)
            {'color': (0, 0, 255), 'vec': np.array([0, 0, -100 * scale])},   # Z (Blue)
            {'color': (255, 255, 255), 'vec': np.array([x_val* 40 * scale, y_val * 40 * scale, z_val * 40 * scale])},
            {'color': (0, 0, 255), 'vec': np.array([a[0] * 40 * scale, a[1] * 40 * scale, a[2] * 40 * scale])},
            {'color': (255, 255, 0), 'vec': np.array([b[0] * 40 * scale, b[1] * 40 * scale, b[2] * 40 * scale])},
            {'color': (255, 0, 255), 'vec': np.array([c[0] * 40 * scale, c[1] * 40 * scale, c[2] * 40 * scale])}
            ]   
    
    if reset:
        vectors = [
            {'color': (255, 0, 0), 'vec': np.array([100 * scale, 0, 0])},   # X (Red)
            {'color': (0, 255, 0), 'vec': np.array([0, 100 * scale, 0])},   # Y (Green)
            {'color': (0, 0, 255), 'vec': np.array([0, 0, 100 * scale])},   # Z (Blue)
            {'color': (255, 0, 0), 'vec': np.array([-100 * scale, 0, 0])},  # X (Red)
            {'color': (0, 255, 0), 'vec': np.array([0, -100 * scale, 0])},  # Y (Green)
            {'color': (0, 0, 255), 'vec': np.array([0, 0, -100 * scale])},   # Z (Blue)
            {'color': (255, 255, 255), 'vec': np.array([x_val* 40 * scale, y_val * 40 * scale, z_val * 40 * scale])},
            {'color': (0, 0, 255), 'vec': np.array([a[0] * 40 * scale, a[1] * 40 * scale, a[2] * 40 * scale])},
            {'color': (255, 255, 0), 'vec': np.array([b[0] * 40 * scale, b[1] * 40 * scale, b[2] * 40 * scale])},
            {'color': (255, 0, 255), 'vec': np.array([c[0] * 40 * scale, c[1] * 40 * scale, c[2] * 40 * scale])}
        ]
        
    screen.fill((20, 20, 20))
    
    origin = (width // 2, height // 2)
    
    i = 0
    accumulated_vec = np.array([0.0, 0.0, 0.0])
    arm_start = origin
    for v in vectors:
        i += 1
        current_vec = v['vec']
        
        # For arm vectors (indices 7, 8, 9 when is_shown), chain them together
        if is_shown and i > 7:
            end_pos = project(accumulated_vec + current_vec, angle_x, angle_y)
            pygame.draw.line(screen, v['color'], arm_start, end_pos, 3)
            pygame.draw.circle(screen, v['color'], end_pos, 5)
            accumulated_vec += current_vec
            arm_start = end_pos
        else:
            end_pos = project(current_vec, angle_x, angle_y)
            pygame.draw.line(screen, v['color'], origin, end_pos, 3)
            pygame.draw.circle(screen, v['color'], end_pos, 5)
            if i > 6:
                origin = end_pos
    pygame.display.flip()

pygame.quit()