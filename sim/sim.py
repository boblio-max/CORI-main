import pygame
import numpy as np
import sys
import os
import json
import asyncio
import threading
import websockets
import math

# Add parent directory to sys.path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import SERVER_HOST, SERVER_PORT

# Simulation Constants
WIDTH, HEIGHT = 800, 600
BACKGROUND_COLOR = (20, 20, 25)
AXIS_COLOR = (100, 100, 100)
JOINT_COLOR = (255, 255, 255)
LINK_COLORS = [(255, 50, 50), (50, 255, 50), (50, 50, 255), (255, 255, 50)]
LINK_LENGTH = 100  # Visual scale for the links

# Shared state for joint angles
joint_angles = [90.0, 90.0, 90.0, 90.0, 0.0, 0.0]
data_lock = threading.Lock()

async def websocket_client():
    uri = f"ws://{SERVER_HOST}:{SERVER_PORT}"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print(f"Connected to {uri}")
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    with data_lock:
                        # Map A1-A6 to joint_angles
                        joint_angles[0] = data.get("A1", 90.0)
                        joint_angles[1] = data.get("A2", 90.0)
                        joint_angles[2] = data.get("A3", 90.0)
                        joint_angles[3] = data.get("A4", 90.0)
                        joint_angles[4] = data.get("A5", 0.0)
                        joint_angles[5] = data.get("A6", 0.0)
        except Exception as e:
            print(f"Websocket error: {e}. Retrying in 2 seconds...")
            await asyncio.sleep(2)

def start_websocket_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(websocket_client())

def project(point, angle_x, angle_y, scale=1.0):
    # Rotation matrices
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
    
    rotated = rx @ (ry @ point)
    return int(rotated[0] * scale + WIDTH/2), int(rotated[1] * scale + HEIGHT/2)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("CORI Robot 3D Simulation")
    clock = pygame.time.Clock()
    
    # Start websocket client in a background thread
    threading.Thread(target=start_websocket_thread, daemon=True).start()
    
    angle_x, angle_y = -0.5, 0.5
    scale = 1.0
    
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Camera controls
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:  angle_y -= 2 * dt
        if keys[pygame.K_RIGHT]: angle_y += 2 * dt
        if keys[pygame.K_UP]:    angle_x -= 2 * dt
        if keys[pygame.K_DOWN]:  angle_x += 2 * dt
        if keys[pygame.K_q]: scale += 0.5 * dt
        if keys[pygame.K_e]: scale -= 0.5 * dt
        
        screen.fill(BACKGROUND_COLOR)
        
        # Draw ground grid (simple)
        grid_size = 200
        for i in range(-5, 6):
            p1 = project(np.array([i * 40, 100, -200]), angle_x, angle_y, scale)
            p2 = project(np.array([i * 40, 100, 200]), angle_x, angle_y, scale)
            pygame.draw.line(screen, AXIS_COLOR, p1, p2, 1)
            p3 = project(np.array([-200, 100, i * 40]), angle_x, angle_y, scale)
            p4 = project(np.array([200, 100, i * 40]), angle_x, angle_y, scale)
            pygame.draw.line(screen, AXIS_COLOR, p3, p4, 1)

        # Get current angles and shift by -90 to align with physical calibration pose
        with data_lock:
            a1 = np.radians(joint_angles[0] - 90)
            a2 = np.radians(joint_angles[1] - 90)
            a3 = np.radians(joint_angles[2] - 90)
            a4 = np.radians(joint_angles[3] - 90)
        
        # Robot base
        origin = np.array([0, 100, 0])
        
        # Forward Kinematics for visualization
        # Base rotation (A1) around Y axis
        # Shoulder (A2), Elbow (A3), Wrist (A4) in the rotated plane
        
        # Joint 1: Base
        p0 = origin
        
        # Joint 2: Shoulder
        # Rotation A1 around vertical (Y), then A2 relative to horizontal
        v1 = np.array([
            LINK_LENGTH * np.cos(a2) * np.cos(a1),
            -LINK_LENGTH * np.sin(a2), # Pygame Y is down, so negative is up
            LINK_LENGTH * np.cos(a2) * np.sin(a1)
        ])
        p1 = p0 + v1
        
        # Joint 3: Elbow
        v2 = np.array([
            LINK_LENGTH * np.cos(a2 + a3) * np.cos(a1),
            -LINK_LENGTH * np.sin(a2 + a3),
            LINK_LENGTH * np.cos(a2 + a3) * np.sin(a1)
        ])
        p2 = p1 + v2
        
        # Joint 4: Wrist
        v3 = np.array([
            LINK_LENGTH * np.cos(a2 + a3 + a4) * np.cos(a1),
            -LINK_LENGTH * np.sin(a2 + a3 + a4),
            LINK_LENGTH * np.cos(a2 + a3 + a4) * np.sin(a1)
        ])
        p3 = p2 + v3
        
        # Draw Links
        points = [p0, p1, p2, p3]
        projected_points = [project(p, angle_x, angle_y, scale) for p in points]
        
        for i in range(len(projected_points) - 1):
            pygame.draw.line(screen, LINK_COLORS[i], projected_points[i], projected_points[i+1], 5)
            pygame.draw.circle(screen, JOINT_COLOR, projected_points[i], 7)
        pygame.draw.circle(screen, JOINT_COLOR, projected_points[-1], 7)
        
        # HUD
        font = pygame.font.SysFont('Arial', 18)
        text = font.render(f"Angles: A1:{joint_angles[0]:.1f} A2:{joint_angles[1]:.1f} A3:{joint_angles[2]:.1f} A4:{joint_angles[3]:.1f}", True, (255, 255, 255))
        screen.blit(text, (10, 10))
        controls = font.render("Arrows: Rotate Camera | Q/E: Zoom", True, (200, 200, 200))
        screen.blit(controls, (10, HEIGHT - 30))
        
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
