import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cv2
import json
import os
from typing import List

from servers import ws_client
import threading

DATA_DIR = "pcb_dataset"
os.makedirs(DATA_DIR, exist_ok=True)


def get_current_angles_from_user() -> List[float]:
    print("Enter 6 joint angles (A1..A6) for this frame, separated by spaces:")
    while True:
        line = input("> ").strip()
        parts = line.split()
        if len(parts) != 6:
            print("Please enter exactly 6 numbers.")
            continue
        try:
            angles = [float(p) for p in parts]
            return angles
        except ValueError:
            print("Invalid number, try again.")


def main():
    threading.Thread(target=ws_client.start_server, daemon=True).start()

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if not cap.isOpened():
        print("Could not open camera")
        return

    idx = 0
    print("Press 'c' to capture a sample, 'q' to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cv2.putText(frame, "Press 'c' to capture, 'q' to quit",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow("Collect PCB Data", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        if key == ord('c'):
            # 1) Save image
            img_path = os.path.join(DATA_DIR, f"img_{idx:05d}.jpg")
            cv2.imwrite(img_path, frame)
            print(f"Saved frame to {img_path}")

            # 2) Get angles for this frame
            angles = get_current_angles_from_user()

            # 3) Save angles to JSON
            meta_path = os.path.join(DATA_DIR, f"img_{idx:05d}.json")
            with open(meta_path, "w") as f:
                json.dump({"angles": angles}, f)
            print(f"Saved angles {angles} to {meta_path}")

            idx += 1

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()