"""
PCB Robot Arm Control System
==============================
Uses a camera to detect a PCB on a surface, computes inverse kinematics,
and outputs 6 servo angles to grab the PCB.

Servo layout:
  A1 — base yaw       (0–180°, 90 = center)
  A2 — joint 1 pitch  (0–180°, 90 = straight up)
  A3 — joint 2 pitch  (0–180°, 90 = straight up)
  A4 — joint 3 pitch  (0–180°, 90 = straight up)
  A5 — wrist yaw      (0–180°, 90 = center)
  A6 — claw throttle  (-1 = open, +1 = closed)

At all joints = 90 and A6 = 1: arm points straight up, claw closed.
As angles decrease toward 0: arm curls inward and rotates right.
As angles increase toward 180: arm extends/rotates left.

Dependencies:
    pip install opencv-python numpy

For servo output, uncomment the RPi.GPIO or serial sections below
and connect to your servo controller (PCA9685, Arduino, etc.).
"""

import cv2
import numpy as np
import math
import time
from dataclasses import dataclass
from enum import Enum, auto


# ─── Configuration ───────────────────────────────────────────────────────────

# Arm link lengths in cm (measure your physical arm)
L1 = 12.0   # base to joint 2
L2 = 10.0   # joint 2 to joint 3
L3 = 7.0    # joint 3 to wrist/claw tip

# Camera field of view calibration
# These map pixel offsets from center to real-world cm at 1m depth
CAM_FOV_X = 60.0   # horizontal FOV in degrees
CAM_FOV_Y = 45.0   # vertical FOV in degrees
CAM_WIDTH  = 640
CAM_HEIGHT = 480

# Grab approach height above detected PCB surface (cm)
HOVER_HEIGHT_CM  = 8.0   # hover before descending
GRAB_HEIGHT_CM   = 1.5   # actual grab height

# PCB detection: HSV green PCB color range
# Tune these for your specific PCB color under your lighting
PCB_HSV_LOW  = np.array([35, 40, 30])
PCB_HSV_HIGH = np.array([85, 255, 255])

# Servo angle limits
SERVO_MIN = 0
SERVO_MAX = 180


# ─── Data structures ─────────────────────────────────────────────────────────

@dataclass
class ServoAngles:
    a1: float = 90.0   # base yaw
    a2: float = 90.0   # joint 1 pitch
    a3: float = 90.0   # joint 2 pitch
    a4: float = 90.0   # joint 3 pitch
    a5: float = 90.0   # wrist yaw
    a6: float = 1.0    # claw (-1 open, +1 closed)

    def clamp(self):
        for attr in ['a1','a2','a3','a4','a5']:
            setattr(self, attr, max(SERVO_MIN, min(SERVO_MAX, getattr(self, attr))))
        self.a6 = max(-1.0, min(1.0, self.a6))
        return self

    def __str__(self):
        return (f"A1={self.a1:6.1f}°  A2={self.a2:6.1f}°  A3={self.a3:6.1f}°  "
                f"A4={self.a4:6.1f}°  A5={self.a5:6.1f}°  A6={self.a6:+.1f}")


@dataclass
class PCBPose:
    """Detected PCB pose in camera/world coordinates."""
    x_cm: float       # lateral offset from robot center
    y_cm: float       # vertical offset (positive = up)
    z_cm: float       # distance from camera / depth
    angle_deg: float  # PCB rotation in the image plane
    confidence: float # detection confidence 0–1
    bbox: tuple = None  # (cx, cy, w, h) in pixels


class Phase(Enum):
    IDLE     = auto()
    DETECT   = auto()
    APPROACH = auto()
    DESCEND  = auto()
    GRASP    = auto()
    HOLD     = auto()


# ─── PCB Detection ───────────────────────────────────────────────────────────

class PCBDetector:
    """
    Detects a PCB in a camera frame using color segmentation + contour analysis.
    Returns the PCB's estimated pose in world coordinates.
    """

    def __init__(self, cam_width=CAM_WIDTH, cam_height=CAM_HEIGHT,
                 fov_x=CAM_FOV_X, fov_y=CAM_FOV_Y):
        self.cam_w = cam_width
        self.cam_h = cam_height
        self.fov_x = fov_x
        self.fov_y = fov_y

    def pixel_to_world(self, px, py, depth_cm):
        """
        Convert pixel coords to world offsets (cm) at a given depth.
        Assumes pinhole camera model.
        """
        cx = self.cam_w / 2
        cy = self.cam_h / 2
        dx_px = px - cx
        dy_px = py - cy
        # angle per pixel
        deg_per_px_x = self.fov_x / self.cam_w
        deg_per_px_y = self.fov_y / self.cam_h
        x_cm = depth_cm * math.tan(math.radians(dx_px * deg_per_px_x))
        y_cm = depth_cm * math.tan(math.radians(dy_px * deg_per_px_y))
        return x_cm, y_cm

    def estimate_depth(self, contour_area_px, known_pcb_area_cm2=100.0):
        """
        Estimate depth from apparent contour size.
        known_pcb_area_cm2: actual PCB area (default 10x10cm = 100cm²)
        This is a rough estimate — replace with a depth camera or calibration.
        """
        if contour_area_px < 1:
            return 50.0
        # pixels per cm at 1m: calibrate for your camera
        PX_PER_CM_AT_100CM = 8.0
        area_cm2_at_1m = contour_area_px / (PX_PER_CM_AT_100CM ** 2)
        # depth scales inversely with sqrt of area ratio
        depth = 100.0 * math.sqrt(area_cm2_at_1m / known_pcb_area_cm2)
        return max(5.0, min(100.0, depth))

    def detect(self, frame) -> PCBPose | None:
        """
        Detect PCB in frame. Returns PCBPose or None if not found.
        """
        blurred = cv2.GaussianBlur(frame, (7, 7), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        mask = cv2.inRange(hsv, PCB_HSV_LOW, PCB_HSV_HIGH)
        # morphological cleanup
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        # Pick largest contour
        best = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(best)
        if area < 500:  # too small = noise
            return None

        rect = cv2.minAreaRect(best)
        (cx, cy), (w, h), angle = rect

        # minAreaRect angle is -90 to 0; normalise to -90..+90
        if w < h:
            angle = angle + 90

        depth_cm = self.estimate_depth(area)
        x_cm, y_cm = self.pixel_to_world(cx, cy, depth_cm)
        # camera y is inverted vs world y
        y_cm = -y_cm

        confidence = min(1.0, area / (self.cam_w * self.cam_h * 0.05))

        return PCBPose(
            x_cm=x_cm,
            y_cm=y_cm,
            z_cm=depth_cm,
            angle_deg=angle,
            confidence=confidence,
            bbox=(int(cx), int(cy), int(w), int(h))
        )

    def draw_detection(self, frame, pose: PCBPose):
        """Draw detection overlay on frame."""
        if pose is None:
            cv2.putText(frame, "PCB: NOT FOUND", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            return frame

        cx, cy = pose.bbox[0], pose.bbox[1]
        # draw crosshair
        cv2.drawMarker(frame, (cx, cy), (0, 255, 100),
                       cv2.MARKER_CROSS, 20, 2)
        # draw orientation line
        length = 40
        angle_rad = math.radians(pose.angle_deg)
        x2 = int(cx + length * math.cos(angle_rad))
        y2 = int(cy + length * math.sin(angle_rad))
        cv2.arrowedLine(frame, (cx, cy), (x2, y2), (255, 100, 0), 2)

        cv2.putText(frame,
                    f"PCB  x:{pose.x_cm:+.1f}  y:{pose.y_cm:+.1f}  z:{pose.z_cm:.1f}  r:{pose.angle_deg:.1f}deg",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 100), 1)
        cv2.putText(frame, f"conf: {pose.confidence:.2f}",
                    (10, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
        return frame


# ─── Inverse Kinematics ──────────────────────────────────────────────────────

class ArmIK:
    """
    3-DOF planar inverse kinematics for the pitch joints (A2, A3, A4).
    A1 handles yaw (base rotation), A5 handles wrist rotation.
    Coordinate system: origin at base joint, Z up, X forward.
    """

    def __init__(self, l1=L1, l2=L2, l3=L3):
        self.l1 = l1
        self.l2 = l2
        self.l3 = l3

    def solve(self, x_cm: float, y_cm: float, z_cm: float,
              wrist_angle_deg: float = 0.0) -> ServoAngles | None:
        """
        Solve IK for target (x, y, z) in robot base frame (cm).
          x = forward/backward
          y = left/right (handled by A1 separately)
          z = up/down

        wrist_angle_deg: desired wrist pitch angle (for grabbing flat PCBs, keep 0)

        Returns ServoAngles or None if target is unreachable.
        """
        # A1: yaw — rotate base to face the x/y lateral offset
        a1_deg = 90.0 + math.degrees(math.atan2(y_cm, max(x_cm, 0.1)))

        # Horizontal reach and vertical target in the plane of the arm
        r = math.sqrt(x_cm**2 + y_cm**2)   # horizontal reach
        h = z_cm                             # height target

        # Subtract l3 projection (wrist contributes to reach)
        wrist_rad = math.radians(wrist_angle_deg)
        r_eff = r - self.l3 * math.cos(wrist_rad)
        h_eff = h - self.l3 * math.sin(wrist_rad)

        d = math.sqrt(r_eff**2 + h_eff**2)

        # Check reachability
        if d > (self.l1 + self.l2):
            print(f"[IK] Target unreachable: distance {d:.1f} cm > arm reach {self.l1 + self.l2:.1f} cm")
            return None
        if d < abs(self.l1 - self.l2):
            print(f"[IK] Target too close: distance {d:.1f} cm")
            return None

        # Law of cosines for elbow angle
        cos_a3 = (d**2 - self.l1**2 - self.l2**2) / (2 * self.l1 * self.l2)
        cos_a3 = max(-1.0, min(1.0, cos_a3))
        a3_internal = math.acos(cos_a3)   # elbow internal angle (0 = fully extended)

        # Shoulder angle
        alpha = math.atan2(h_eff, r_eff)
        beta = math.acos(max(-1.0, min(1.0,
                   (d**2 + self.l1**2 - self.l2**2) / (2 * d * self.l1))))
        a2_internal = alpha + beta

        # Convert internal angles to servo angles (90° = straight up / neutral)
        # A2: 90 = pointing up; decreasing = curling forward
        a2_deg = 90.0 - math.degrees(a2_internal)
        # A3: 90 = straight; decreasing = elbow bends
        a3_deg = 90.0 + math.degrees(a3_internal)
        # A4: wrist pitch compensation to keep claw level
        a4_deg = 90.0 + wrist_angle_deg - (math.degrees(a2_internal) - math.degrees(a3_internal)) * 0.3

        return ServoAngles(
            a1=a1_deg,
            a2=a2_deg,
            a3=a3_deg,
            a4=a4_deg,
            a5=90.0,   # wrist yaw set separately based on PCB rotation
            a6=1.0     # claw default closed; caller overrides
        ).clamp()


# ─── Robot Controller ─────────────────────────────────────────────────────────

class RobotController:
    """
    High-level sequencer: runs the detect → approach → descend → grasp → hold pipeline.
    """

    def __init__(self):
        self.detector = PCBDetector()
        self.ik = ArmIK()
        self.phase = Phase.IDLE
        self.current_angles = ServoAngles()
        self.target_pose: PCBPose | None = None

    # ── Servo output ────────────────────────────────────────────────────────
    def send_angles(self, angles: ServoAngles):
        """
        Send angles to servo controller.
        Replace the print() with your actual hardware interface.

        Examples:
          # Raspberry Pi PCA9685 via adafruit-circuitpython-servokit:
          #   kit.servo[0].angle = angles.a1
          #   ...
          # Arduino over serial:
          #   ser.write(f"{angles.a1},{angles.a2},{angles.a3},{angles.a4},{angles.a5},{angles.a6}\n".encode())
        """
        self.current_angles = angles
        print(f"  SERVO OUT → {angles}")

    def interpolate_to(self, target: ServoAngles, steps: int = 20, delay: float = 0.03):
        """Smoothly interpolate from current angles to target over N steps."""
        src = self.current_angles
        for i in range(1, steps + 1):
            t = i / steps
            ease = t * t * (3 - 2 * t)   # smoothstep
            interp = ServoAngles(
                a1 = src.a1 + (target.a1 - src.a1) * ease,
                a2 = src.a2 + (target.a2 - src.a2) * ease,
                a3 = src.a3 + (target.a3 - src.a3) * ease,
                a4 = src.a4 + (target.a4 - src.a4) * ease,
                a5 = src.a5 + (target.a5 - src.a5) * ease,
                a6 = src.a6 + (target.a6 - src.a6) * ease,
            ).clamp()
            self.send_angles(interp)
            time.sleep(delay)

    # ── Phase handlers ───────────────────────────────────────────────────────
    def phase_idle(self):
        print("\n[IDLE] Moving to home position (all joints 90°, claw closed)")
        self.interpolate_to(ServoAngles())  # all defaults = 90°, a6=1
        self.phase = Phase.DETECT

    def phase_detect(self, frame) -> bool:
        """Returns True when a confident detection is locked."""
        pose = self.detector.detect(frame)
        if pose and pose.confidence > 0.4:
            self.target_pose = pose
            print(f"\n[DETECT] PCB locked:")
            print(f"  Position → x:{pose.x_cm:+.1f}cm  y:{pose.y_cm:+.1f}cm  z:{pose.z_cm:.1f}cm")
            print(f"  Rotation → {pose.angle_deg:.1f}°   confidence: {pose.confidence:.2f}")
            self.phase = Phase.APPROACH
            return True
        return False

    def phase_approach(self):
        """Move claw to hover above PCB, claw open, wrist aligned to PCB rotation."""
        p = self.target_pose
        print(f"\n[APPROACH] Hovering {HOVER_HEIGHT_CM}cm above PCB, opening claw")

        # Target: above PCB center at hover height, claw open
        angles = self.ik.solve(
            x_cm = p.z_cm,             # depth = forward reach
            y_cm = p.x_cm,             # lateral offset = y in arm frame
            z_cm = HOVER_HEIGHT_CM     # hover height
        )
        if angles is None:
            print("[APPROACH] IK failed — target out of reach")
            return False

        # Align wrist to PCB rotation
        angles.a5 = 90.0 + p.angle_deg * 0.5
        angles.a6 = -1.0   # open claw
        angles.clamp()

        print(f"  Target angles: {angles}")
        self.interpolate_to(angles, steps=30)
        self.phase = Phase.DESCEND
        return True

    def phase_descend(self):
        """Lower claw to grab height."""
        p = self.target_pose
        print(f"\n[DESCEND] Lowering to grab height {GRAB_HEIGHT_CM}cm")

        angles = self.ik.solve(
            x_cm = p.z_cm,
            y_cm = p.x_cm,
            z_cm = GRAB_HEIGHT_CM
        )
        if angles is None:
            print("[DESCEND] IK failed")
            return False

        angles.a5 = 90.0 + p.angle_deg * 0.5
        angles.a6 = -1.0   # still open
        angles.clamp()

        print(f"  Target angles: {angles}")
        self.interpolate_to(angles, steps=20)
        time.sleep(0.3)   # brief pause before grabbing
        self.phase = Phase.GRASP
        return True

    def phase_grasp(self):
        """Close the claw."""
        print("\n[GRASP] Closing claw")
        closed = ServoAngles(**vars(self.current_angles))
        closed.a6 = 1.0
        self.interpolate_to(closed, steps=10, delay=0.05)
        time.sleep(0.4)
        print("[GRASP] Claw closed — PCB secured")
        self.phase = Phase.HOLD

    def phase_hold(self):
        print("\n[HOLD] Holding position. Press Q to release and reset.")
        # Just keeps current angles — no movement

    # ── Main run loop ────────────────────────────────────────────────────────
    def run(self, camera_index: int = 0):
        cap = cv2.VideoCapture(camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

        if not cap.isOpened():
            print(f"[ERROR] Cannot open camera {camera_index}")
            return

        print("=" * 60)
        print("  PCB Robot Arm Control System")
        print("  Press SPACE to start sequence, Q to quit/reset")
        print("=" * 60)

        self.phase = Phase.IDLE
        sequence_started = False

        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Frame read failed")
                break

            # Always show detection overlay
            pose = self.detector.detect(frame)
            display = frame.copy()
            display = self.detector.draw_detection(display, pose)

            # Phase label
            phase_color = {
                Phase.IDLE:     (180, 180, 180),
                Phase.DETECT:   (0, 200, 255),
                Phase.APPROACH: (200, 100, 255),
                Phase.DESCEND:  (0, 180, 255),
                Phase.GRASP:    (0, 255, 100),
                Phase.HOLD:     (0, 255, 180),
            }.get(self.phase, (255, 255, 255))
            cv2.putText(display, f"Phase: {self.phase.name}", (10, CAM_HEIGHT - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, phase_color, 2)

            # Angle readout
            a = self.current_angles
            cv2.putText(display,
                        f"A1:{a.a1:.0f} A2:{a.a2:.0f} A3:{a.a3:.0f} A4:{a.a4:.0f} A5:{a.a5:.0f} A6:{a.a6:+.1f}",
                        (10, CAM_HEIGHT - 36), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

            cv2.imshow("PCB Robot Arm", display)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                if self.phase == Phase.HOLD:
                    print("\n[RESET] Releasing PCB and returning to home")
                    release = ServoAngles(**vars(self.current_angles))
                    release.a6 = -1.0
                    self.interpolate_to(release, steps=8)
                    time.sleep(0.5)
                    self.phase = Phase.IDLE
                    sequence_started = False
                else:
                    break

            elif key == ord(' ') and not sequence_started:
                sequence_started = True
                self.phase = Phase.IDLE

            if sequence_started:
                if self.phase == Phase.IDLE:
                    self.phase_idle()

                elif self.phase == Phase.DETECT:
                    self.phase_detect(frame)

                elif self.phase == Phase.APPROACH:
                    self.phase_approach()

                elif self.phase == Phase.DESCEND:
                    self.phase_descend()

                elif self.phase == Phase.GRASP:
                    self.phase_grasp()

                elif self.phase == Phase.HOLD:
                    self.phase_hold()

        cap.release()
        cv2.destroyAllWindows()


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PCB Robot Arm Controller")
    parser.add_argument("--camera", type=int, default=0, help="Camera device index (default 0)")
    parser.add_argument("--demo", action="store_true", help="Run IK demo without camera")
    args = parser.parse_args()

    if args.demo:
        print("── IK Demo ─────────────────────────────────────────────")
        ik = ArmIK()
        test_cases = [
            (20, 0, 5,  "center forward, near floor"),
            (15, 5, 8,  "slight right, medium height"),
            (10, -5, 10, "slight left, higher up"),
            (25, 8, 3,  "far right, low"),
        ]
        for x, y, z, desc in test_cases:
            result = ik.solve(x, y, z)
            if result:
                print(f"\nTarget ({x:+.0f}, {y:+.0f}, {z:+.0f}) cm — {desc}")
                print(f"  {result}")
            else:
                print(f"\nTarget ({x}, {y}, {z}) — UNREACHABLE")
    else:
        controller = RobotController()
        controller.run(camera_index=args.camera)