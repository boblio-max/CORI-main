import numpy as np

class IKSolver:
    def __init__(self, L=1.0):
        self.L = L
    
    def solve_angles(self, fx, fy, fz):
        """
        Solves for joint angles given a target (fx, fy, fz).
        Assumes:
        - A1: Base rotation (Center at 90)
        - A2: Shoulder (Vertical at 90)
        - A3: Elbow (Straight at 90)
        - A4: Wrist Pitch (Straight at 90)
        """
        # A1: Base Rotation
        # Use arctan2(x, y) where y is depth and x is side-to-side
        # This allows the robot to point at any coordinate in the plane
        A1_rad = np.arctan2(fx, fy) 
        
        # Horizontal distance in the plane
        r = np.hypot(fx, fy)
        # Vertical height
        s = fz

        L1 = self.L
        L2 = self.L

        dist = np.hypot(r, s)
        max_reach = L1 + L2

        if dist > max_reach:
            scale = max_reach / dist
            r *= scale
            s *= scale
            dist = max_reach
            
        # Law of Cosines for A3 (Elbow)
        cos_A3 = (r**2 + s**2 - L1**2 - L2**2) / (2 * L1 * L2)
        cos_A3 = np.clip(cos_A3, -1.0, 1.0)
        A3_rad = np.arccos(cos_A3)
        
        # A2 (Shoulder)
        k1 = L1 + L2 * np.cos(A3_rad)
        k2 = L2 * np.sin(A3_rad)
        A2_rad = np.arctan2(s, r) - np.arctan2(k2, k1)
        
        # A4 (Wrist Pitch) - Keep it relative to the arm or pointing forward
        A4_rad = -(A2_rad + A3_rad)

        # Map to 0-180 with 90 as the neutral center
        # A1: 0 is left, 90 is center, 180 is right
        a1_deg = np.degrees(A1_rad) + 90
        
        # A2: 90 is vertical (upright)
        a2_deg = np.degrees(A2_rad) + 90
        
        # A3: 90 is straight relative to shoulder
        a3_deg = np.degrees(A3_rad) + 90
        
        # A4: 90 is straight relative to elbow
        a4_deg = np.degrees(A4_rad) + 90
        
        return {
            'A1': float(a1_deg),
            'A2': float(a2_deg),
            'A3': float(a3_deg),
            'A4': float(a4_deg)
        }
        
    def solve_vectors(self, fx, fy, fz):
        # Simplified vector calculation for visualization
        res = self.solve_angles(fx, fy, fz)
        a1 = np.radians(res['A1'] - 90)
        a2 = np.radians(res['A2'] - 90)
        a3 = np.radians(res['A3'] - 90)
        a4 = np.radians(res['A4'] - 90)
        
        A = np.array([0.0, 0.0, 0.0])
        # Note: Mapping for visualization might vary by coordinate system
        B = np.array([self.L * np.cos(a2) * np.sin(a1), self.L * np.cos(a2) * np.cos(a1), self.L * np.sin(a2)])
        C = B + np.array([self.L * np.cos(a2 + a3) * np.sin(a1), self.L * np.cos(a2 + a3) * np.cos(a1), self.L * np.sin(a2 + a3)])   
        D = C + np.array([self.L * np.cos(a2 + a3 + a4) * np.sin(a1), self.L * np.cos(a2 + a3 + a4) * np.cos(a1), self.L * np.sin(a2 + a3 + a4)])
        
        return B - A, C - B, D - C

    def update_from_vector(self, fx, fy, fz):
        return self.solve_vectors(float(fx), float(fy), float(fz))
