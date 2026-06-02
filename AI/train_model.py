import os
import json
from glob import glob
from typing import List, Tuple

import cv2
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

# ---------------------------
# Same settings as runtime
# ---------------------------
FEATURE_SIZE = 32
INPUT_DIM = FEATURE_SIZE * FEATURE_SIZE


class AngleNet(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 6),
            nn.Sigmoid(),  # (0,1)
        )

    def forward(self, x):
        return self.net(x) * 180.0


def frame_to_features(frame) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (FEATURE_SIZE, FEATURE_SIZE))
    feat = small.astype(np.float32) / 255.0
    return feat.flatten()


class PcbDataset(Dataset):
    def __init__(self, data_dir: str):
        self.samples: List[Tuple[str, str]] = []  # (img_path, json_path)

        img_paths = sorted(glob(os.path.join(data_dir, "img_*.jpg")))
        for img_path in img_paths:
            base = os.path.splitext(os.path.basename(img_path))[0]
            json_path = os.path.join(data_dir, base + ".json")
            if os.path.exists(json_path):
                self.samples.append((img_path, json_path))

        if not self.samples:
            raise RuntimeError(f"No samples found in {data_dir}")

        print(f"Found {len(self.samples)} samples")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, json_path = self.samples[idx]

        frame = cv2.imread(img_path)
        feats = frame_to_features(frame)

        with open(json_path, "r") as f:
            meta = json.load(f)
        angles = meta["angles"]  # list of 6 numbers

        x = torch.from_numpy(feats).float()  # [INPUT_DIM]
        y = torch.tensor(angles, dtype=torch.float32)  # [6]

        return x, y


def train(data_dir="pcb_dataset", epochs=20, batch_size=16, lr=1e-3):
    dataset = PcbDataset(data_dir)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model = AngleNet(INPUT_DIM)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    model.train()

    for epoch in range(1, epochs + 1):
        total_loss = 0.0
        for x, y in dataloader:
            # x: [B, INPUT_DIM], y: [B, 6]
            pred = model(x)
            loss = criterion(pred, y)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * x.size(0)

        avg_loss = total_loss / len(dataset)
        print(f"Epoch {epoch}/{epochs} - Loss: {avg_loss:.4f}")

    # Save model
    os.makedirs("models", exist_ok=True)
    save_path = os.path.join("models", "angles_model.pt")
    torch.save(model.state_dict(), save_path)
    print(f"Saved trained model to {save_path}")


if __name__ == "__main__":
    train()