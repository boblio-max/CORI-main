import numpy as np

class IKSolver:
    def __init__(self, L=1.0):
        self.L = L
    
    def solve_angles(self, fx, fy, fz):
        A1 = np.arctan2(fy, fx)
        r = np.hypot(fx, fy)
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
            
        cos_A3 = (r**2 + s**2 - L1**2 - L2**2) / (2 * L1 * L2)
        cos_A3 = np.clip(cos_A3, -1.0, 1.0)
        A3 = np.arccos(cos_A3)
        
        k1 = L1 + L2 * np.cos(A3)
        k2 = L2 * np.sin(A3)

        A2 = np.arctan2(s, r) - np.arctan2(k2, k1)
        A4 = -(A2 + A3)

        return {
            'A1': float(np.degrees(A1)),
            'A2': float(np.degrees(A2)),
            'A3': float(np.degrees(A3)),
            'A4': float(np.degrees(A4))
        }
        
    def solve_vectors(self, fx, fy, fz):
        angles = self.solve_angles(fx, fy, fz)

        A1 = np.radians(angles['A1'])
        A2 = np.radians(angles['A2'])
        A3 = np.radians(angles['A3'])
        A4 = np.radians(angles['A4'])
    
        A1 = np.arctan2(fy, fx)
        
        r = np.hypot(fx, fy)
        s = fz
        
        dist = np.hypot(r, s)
        max_reach = self.L * 3
        
        if dist > max_reach:
            scale = max_reach / dist
            r *= scale
            s *= scale
        
        
        angles = self.solve_angles(fx, fy, fz)
        
        A = np.array([0.0, 0.0, 0.0])
        B = np.array([self.L * np.cos(A2) * np.cos(A1), self.L * np.cos(A2) * np.sin(A1), self.L * np.sin(A2)])
        C = B + np.array([self.L * np.cos(A2 + A3) * np.cos(A1), self.L * np.cos(A2 + A3) * np.sin(A1), self.L * np.sin(A2 + A3)])   
        D = C + np.array([self.L * np.cos(A2 + A3 + A4) * np.cos(A1), self.L * np.cos(A2 + A3 + A4) * np.sin(A1), self.L * np.sin(A2 + A3 + A4)])
        
        AtB = B - A
        BtC = C - B
        CtD = D - C
        
        return AtB, BtC, CtD
    
    def update_from_string(self, data_str):
        try:
            data = data_str.split(',')
            return self.solve_angles(float(data[0]), float(data[1]), float(data[2]))
        except (IndexError, ValueError):
            print("Invalid input format. Expected 'fx,fy,fz'.")
            return None

    def update_from_vector(self, fx, fy, fz):
        return self.solve_vectors(float(fx), float(fy), float(fz))
    