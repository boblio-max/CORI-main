import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cv2
import base64
import json
from typing import List

import g4f
from servers import ws_client
import threading
threading.Thread(target=ws_client.start_server, daemon=True).start()

MODEL_NAME = "gpt-4o-mini"  

SYSTEM_PROMPT = """You control a 6-DOF robot arm holding a PCB.
Your job is to choose 6 joint angles so the PCB is in a good position
and orientation for a human to solder components.

Angle conventions (A1..A6):
- 0°   = joint fully curled one way (like an arm pulled in)
- 90°  = neutral, straight up and pointing straight
- 180° = fully curled the opposite way

Requirements:
- The PCB should appear flat, not tilted away from the camera.
- Prefer poses where the PCB is centered in front of the camera,
  with its surface roughly perpendicular to the camera.
- Avoid extreme angles that would twist cables or collide with the table.

CRITICAL:
- Always output exactly 6 numbers.
- Each number must be between 0 and 180.
- Output ONLY a JSON list of 6 numbers, e.g.: [90, 90, 90, 90, 90, 90]
"""

USER_PROMPT_TEMPLATE = """You are given a base64-encoded camera frame.
It shows the workspace containing a robot arm and a PCB that should be
held in a good position for soldering.

The image is encoded as base64 below:

IMAGE_BASE64_START
{image_b64}
IMAGE_BASE64_END

Choose 6 joint angles (A1..A6) in degrees that make the robot hold the PCB
in a good position for a human to solder:
- PCB should be centered in front of the camera
- PCB surface should be roughly facing the camera
- Avoid obviously dangerous or impossible poses

Remember:
- 0  = fully curled one way
- 90 = straight / neutral
- 180 = fully curled the other way

Output ONLY a JSON list of 6 numbers, nothing else.
"""


def clamp_angle(a: float) -> float:
    return max(0.0, min(180.0, float(a)))


def parse_angles(text: str) -> List[float]:
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON array found in response: {text!r}")

    arr_str = text[start : end + 1]
    arr = json.loads(arr_str)

    if not isinstance(arr, list) or len(arr) != 6:
        raise ValueError(f"Expected list of 6 numbers, got: {arr!r}")

    return [clamp_angle(x) for x in arr]


def frame_to_base64(frame) -> str:
    # Compress to JPEG then encode
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        raise RuntimeError("Failed to encode frame")
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def get_robot_angles_from_frame(frame) -> List[float]:
    image_b64 = frame_to_base64(frame)
    user_prompt = USER_PROMPT_TEMPLATE.format(image_b64=image_b64)

    response = g4f.ChatCompletion.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    # Normalize response to a string
    if isinstance(response, str):
        text = response
    else:
        try:
            text = response["choices"][0]["message"]["content"]
        except Exception:
            text = str(response)

    return parse_angles(text)


def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if not cap.isOpened():
        print("Could not open camera")
        return

    # To avoid spamming the model on every frame (slow + expensive),
    # only query every N frames or when you press a key.
    frame_count = 0
    N = 30  


    angles = [90.0] * 6

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        # Show current view
        cv2.putText(frame, "Press 'a' to query AI, 'q' to quit",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow("PCB View", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

        # Option 1: only query when you press 'a'
        if key == ord('a'):
            try:
                new_angles = get_robot_angles_from_frame(frame)
                angles = new_angles
                print("AI angles:", angles)
            except Exception as e:
                print("AI error:", e)

        # Option 2 (commented): automatically query every N frames
        # if frame_count % N == 0:
        #     try:
        #         new_angles = get_robot_angles_from_frame(frame)
        #         angles = new_angles
        #         print("AI angles:", angles)
        #     except Exception as e:
        #         print("AI error:", e)

        with ws_client.data_lock:
            ws_client.data["A1"] = angles[0]
            ws_client.data["A2"] = angles[1]
            ws_client.data["A3"] = angles[2]
            ws_client.data["A4"] = angles[3]
            ws_client.data["A5"] = angles[4]
            ws_client.data["A6"] = angles[5]

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()