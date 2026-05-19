import numpy as np

class IKSolver:
    def __init__(self, L=1.0):
        self.L = L
    
    def solve_angles(self, fx, fy, fz):
        A2, A3, A4 = 0.0, 0.0, 0.0
        
        A1 = np.arctan2(fy, fx)
        
        r = np.hypot(fx, fy)
        s = fz
        
        dist = np.hypot(r, s)
        max_reach = self.L * 3
        
        if dist > max_reach:
            scale = max_reach / dist
            r *= scale
            s *= scale
        
        
        # Special case
        if r == 0 and s == 0:
            A2 = np.arctan2(s, 0)
            A3 = A4 = 0.0
            
        else:
            c2 = (r**2 + s**2 - 2 * (3*self.L ** 2)) / (2 * self.L**2)
            c2 = np.clip(c2, -1.0, 1.0)
            A2 = np.arctan2(s,r) - np.arctan2(np.sqrt(1 - c2**2), c2)
            
            A3 = np.arccos(np.clip((r - self.L*np.cos(A2)) / self.L, -1.0, 1.0)) - A2

        return {
            'A1': float(np.degrees(A1)),
            'A2': float(np.degrees(A2)),
            'A3': float(np.degrees(A3)),
            'A4': float(np.degrees(A4))
        }
        
        
    def solve_vectors(self, fx, fy, fz):
        A2, A3, A4 = 0.0, 0.0, 0.0
    
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
    