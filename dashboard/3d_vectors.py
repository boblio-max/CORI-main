# IMPORTS + PARENT DIRECTORY SETUP
import pygame
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Robot_math import ik_solver

# Initialize the inverse kinematics solver and Pygame
vector = ik_solver.IKSolver(L=1.0)
pygame.init()
pygame.joystick.init()

# Board constants
width, height = 800, 600

# Creating the screen and setting up the clock for controlling frame rate
screen = pygame.display.set_mode((width, height))
clock = pygame.time.Clock()
pygame.display.set_caption("3D Vector Visualization")

# Joystick setup
joysticks = []
for i in range(pygame.joystick.get_count()):
    joy = pygame.joystick.Joystick(i)
    joy.init()
    joysticks.append(joy)
    
# Initial angles(rotation) and vector values
angle_x, angle_y = 0, 0
x_val, y_val, z_val = 0, 0, 0

# Arm constants for each segment of the ARM
L = 1
Lm = 1.57079
A1 = 0
A2 = 0
A3 = 0
A4 = 0
x = 0.5  
x_val, y_val, z_val = 0.5, 0.5, 0.5
# Resultant vector
n = (x_val, y_val, z_val)

# Made with AI
def project(vector, angle_x, angle_y):
    
    # Converts the 3d vectors y/z rotation to 2d coordinates for drawing on the screen
    ry = np.array([
        [np.cos(angle_y), 0, np.sin(angle_y)],
        [0, 1, 0],
        [-np.sin(angle_y), 0, np.cos(angle_y)]
    ])
    
    # Converts the 3d vectors x/z rotation to 2d coordinates for drawing on the screen
    rx = np.array([
        [1, 0, 0],
        [0, np.cos(angle_x), -np.sin(angle_x)],
        [0, np.sin(angle_x), np.cos(angle_x)]
    ])
    
    # applied the rotations to the vector and then translates it to the center of the screen for drawing
    rotated = rx @ (ry @ vector)
    return int(rotated[0] + width/2), int(rotated[1] + height/2)

# Main loop variables
scale = 1.0
is_shown = True
reset = False

# Main loop
running = True
while running:
    # Control frame rate and get time delta for smooth movement
    dt = clock.tick(60) / 1000.0
    
    # Checks for events (like quitting the application)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    # Get joystick input and calculate the corresponding angles using inverse kinematics
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
    
    # Sets the resultant vector based on joystick input (scaled for better visualization)
    n = (x_val * 30, y_val * 30, z_val * 30)
    
    # If a key is pressed, adjust the camera angles and scale based on user input for better visualization
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:  
        angle_y -= 2 * dt
    if keys[pygame.K_RIGHT]: 
        angle_y += 2 * dt
    if keys[pygame.K_UP]:    
        angle_x -= 2 * dt
    if keys[pygame.K_DOWN]: 
        angle_x += 2 * dt
    
    # If page up/down keys are pressed, adjust the scale of the visualization
    if keys[pygame.K_PAGEUP]:
        scale += 0.1
    if keys[pygame.K_PAGEDOWN]:
        if scale > 0.0:
            scale -= 0.1
        else:
            scale = 0
            
    # if R is pressed, reset the camera angles and scale to default values
    if keys[pygame.K_r]:
        scale = 1.0
        angle_x, angle_y = 0, 0
    
    # If S is pressed, toggle the visibility of the arm vectors
    if keys[pygame.K_s]:
        reset = not reset
    
    # if X, Y, or Z is pressed, set the camera to predefined angles based on axes 
    if keys[pygame.K_x]:
        angle_x, angle_y = 1.63, 1.57
    if keys[pygame.K_y]:
        angle_x, angle_y = 0.03, 0
    if keys[pygame.K_z]:
        angle_x, angle_y = 1.56, 0

    # Calculate the arm vectors using inverse kinematics
    a, b, c = vector.update_from_vector(n[0], n[1], n[2])
    
    # Define the vectors to be drawn, including the coordinate axes and the resultant vector from joystick input
    # The first 6 are the axis vectors, and the 7th is the resultant vector from joystick input. 
    vectors = [
            {'color': (255, 0, 0), 'vec': np.array([100 * scale, 0, 0])},   # X (Red)
            {'color': (0, 255, 0), 'vec': np.array([0, 100 * scale, 0])},   # Y (Green)
            {'color': (0, 0, 255), 'vec': np.array([0, 0, 100 * scale])},   # Z (Blue)
            {'color': (255, 0, 0), 'vec': np.array([-100 * scale, 0, 0])},  # X (Red)
            {'color': (0, 255, 0), 'vec': np.array([0, -100 * scale, 0])},  # Y (Green)
            {'color': (0, 0, 255), 'vec': np.array([0, 0, -100 * scale])},   # Z (Blue)
            {'color': (255, 255, 255), 'vec': np.array([x_val* 40 * scale, y_val * 40 * scale, z_val * 40 * scale])}
        ]

    # If the arm vectors are toggled to be shown, The arm vectors (a, b, c) 
    # are added to the list of vectors to be drawn with different colors for each segment of the arm.
    if is_shown or reset:
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
    
    # Drawing the vectors on the screen
    screen.fill((20, 20, 20))
    
    # Getting the center of the screen to use as the origin for drawing the vectors
    origin = (width // 2, height // 2)
    
    # Drawing the vectors
    i = 0
    accumulated_vec = np.array([0.0, 0.0, 0.0])
    arm_start = origin
    for v in vectors:
        i += 1
        current_vec = v['vec']
        
        # For arm vectors (indices 7, 8, 9 when is_shown), chain them together
        # Simple pygame line drawing with the projected 2D coordinates of the 3D vectors, using different colors for each vector
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