import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cv2
from typing import List

import threading
import numpy as np

import torch
import torch.nn as nn

from servers import ws_client

# ---------------------------
# PyTorch model definition
# ---------------------------

FEATURE_SIZE = 32  # image will be resized to 32x32 grayscale
INPUT_DIM = FEATURE_SIZE * FEATURE_SIZE  # flattened features -> 1024


def clamp_angle(a: float) -> float:
    return max(0.0, min(180.0, float(a)))


class AngleNet(nn.Module):
    """Tiny MLP that maps flattened image features -> 6 joint angles (0–180)."""

    def __init__(self, input_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 6),
            nn.Sigmoid(),  # outputs in (0,1)
        )

    def forward(self, x):
        # x: [batch, input_dim]
        out = self.net(x)
        # scale to [0, 180]
        return out * 180.0


def frame_to_features(frame) -> np.ndarray:
    """Convert BGR frame (OpenCV) to a normalized 1D feature vector."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (FEATURE_SIZE, FEATURE_SIZE))
    feat = small.astype(np.float32) / 255.0
    return feat.flatten()


# Initialize model
model = AngleNet(INPUT_DIM)

# Try to load trained weights
model_dir = os.path.join(os.path.dirname(__file__), "models")
model_path = os.path.join(model_dir, "angles_model.pt")
if os.path.exists(model_path):
    model.load_state_dict(torch.load(model_path, map_location="cpu"))
    print("Loaded trained model from", model_path)
else:
    print("Warning: trained model not found at", model_path, "— using random weights")

model.eval()


def get_robot_angles_from_frame(frame) -> List[float]:
    """Compute 6 joint angles from a camera frame using the trained PyTorch model."""
    feats = frame_to_features(frame)  # numpy, shape (INPUT_DIM,)
    x = torch.from_numpy(feats).unsqueeze(0)  # [1, INPUT_DIM]

    with torch.no_grad():
        angles_tensor = model(x)[0]  # [6]

    angles = angles_tensor.tolist()
    return [clamp_angle(a) for a in angles]


def main():
    # Start WebSocket server in background (for CORI interface)
    threading.Thread(target=ws_client.start_server, daemon=True).start()

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if not cap.isOpened():
        print("Could not open camera")
        return

    frame_count = 0
    N = 30  # if you want auto-update every N frames as well

    # Start from a neutral pose
    angles = [90.0] * 6

    print("Press 'a' to run PyTorch model, 'q' to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        # Draw instructions
        cv2.putText(frame, "Press 'a' for AI (PyTorch), 'q' to quit",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow("PCB View", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

        # Manual trigger: press 'a' to query local model
        if key == ord('a'):
            try:
                new_angles = get_robot_angles_from_frame(frame)
                angles = new_angles
                print("PyTorch angles:", [round(a, 1) for a in angles])
            except Exception as e:
                print("PyTorch error:", e)

        # Optional: auto-query every N frames
        if frame_count % N == 0:
            try:
                new_angles = get_robot_angles_from_frame(frame)
                angles = new_angles
                print("PyTorch angles (auto):", [round(a, 1) for a in angles])
            except Exception as e:
                print("PyTorch error (auto):", e)

        # Send angles to WebSocket server (CORI)
        with ws_client.data_lock:
            ws_client.data["A1"] = angles[0]
            ws_client.data["A2"] = angles[1]
            ws_client.data["A3"] = angles[2]
            ws_client.data["A4"] = angles[3]
            ws_client.data["A5"] = angles[4]
            # Convert A6 from degrees (0..180) to standardized throttle (-1..1)
            ws_client.data["A6"] = (float(angles[5]) - 90.0) / 90.0

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()