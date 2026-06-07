# IMPORTS
import numpy as np

# IKSolver - 
# This class is responsible for calculating the angles of the robot's joints based on the 
# desired position of the end effector.
class IKSolver:
    # Sets the length of the robot arm segments
    def __init__(self, L=1.0):
        self.L = L
    
    # I FIRST MADE THIS IN DESMOS, THEN CONVERTED IT TO PYTHON, SO IT LOOKS A LITTLE WEIRD
    # DESMOS ALSO USED REGRESSION TO FIND THE BEST CONSTANTS, AND I COULDN't FIGURE OUT HOW TO DO THAT IN PYTHON, 
    # SO WITH THE HELP OF ANTIGRAVITY I USED DIFFERENT TRIG IDENTITIES TO FIND THE BEST CONSTANTS 
    # YAY MORE TRIG
    
    # Solves the angles of the robot's joints based on the desired position of the end effector
    # RETURNS ANGLES IN DEGREES
    def solve_angles(self, fx, fy, fz):
        
        # A1 is the angle of the base rotation, calculated using atan2 to get the correct quadrant
        A1 = np.arctan2(fy, fx)
        
        # R is the distance from the base to the projection of the end effector on the XY plane, 
        # and S is the height of the end effector
        r = np.hypot(fx, fy)
        s = fz

        # L1 and L2 are the lengths of the robot arm segments, which are both set to L 
        L1 = self.L
        L2 = self.L

        # The distance from the base to the end effector is calculated, and if it's greater than the maximum reach of the arm,
        # then we scale back to the maximum reach while maintaining the direction
        dist = np.hypot(r, s)
        max_reach = L1 + L2
        if dist > max_reach:
            scale = max_reach / dist
            r *= scale
            s *= scale
            dist = max_reach
            
        # Using the law of cosines to calculate the angle A3 at the elbow joint, and then calculating A2 and A4 based on A3
        cos_A3 = (r**2 + s**2 - L1**2 - L2**2) / (2 * L1 * L2)
        cos_A3 = np.clip(cos_A3, -1.0, 1.0)
        A3 = np.arccos(cos_A3)
        
        # K1 and K2 are intermediate values used to calculate A2, 
        # which is the angle of the shoulder joint, and A4, which is the angle of the wrist joint
        k1 = L1 + L2 * np.cos(A3)
        k2 = L2 * np.sin(A3)

        # A2 is calculated using atan2 to get the correct quadrant,
        # and A4 is calculated to ensure the end effector points in the correct direction
        A2 = np.arctan2(s, r) - np.arctan2(k2, k1)
        A4 = -(A2 + A3)

        # Returns the angles in degrees
        return {
            'A1': float(np.degrees(A1)),
            'A2': float(np.degrees(A2)),
            'A3': float(np.degrees(A3)),
            'A4': float(np.degrees(A4))
        }
        
    # Solves the vectors of the robot's joints based on the desired position of the end effector
    # RETURNS VECTORS FOR EACH ARM SEGMENT
    def solve_vectors(self, fx, fy, fz):
        # A1 is the angle of the base rotation, calculated using atan2 to get the correct quadrant
        A1 = np.arctan2(fy, fx)
        
        # R is the distance from the base to the projection of the end effector on the XY plane,
        # and S is the height of the end effector
        r = np.hypot(fx, fy)
        s = fz
        
        # The distance from the base to the end effector is calculated, and if it's greater than the maximum reach of the arm,
        # then we scale back to the maximum reach while maintaining the direction
        dist = np.hypot(r, s)
        max_reach = self.L * 3
        if dist > max_reach:
            scale = max_reach / dist
            r *= scale
            s *= scale
        
        # Calculate the angles 
        angles = self.solve_angles(fx, fy, fz)
        A1 = np.radians(angles['A1'])
        A2 = np.radians(angles['A2'])
        A3 = np.radians(angles['A3'])
        A4 = np.radians(angles['A4'])
        
        # Use the angles to calculate the position of each joint in 3D space, starting from the base (A) to the end effector (D)
        A = np.array([0.0, 0.0, 0.0])
        B = np.array([self.L * np.cos(A2) * np.cos(A1), self.L * np.cos(A2) * np.sin(A1), self.L * np.sin(A2)])
        C = B + np.array([self.L * np.cos(A2 + A3) * np.cos(A1), self.L * np.cos(A2 + A3) * np.sin(A1), self.L * np.sin(A2 + A3)])   
        D = C + np.array([self.L * np.cos(A2 + A3 + A4) * np.cos(A1), self.L * np.cos(A2 + A3 + A4) * np.sin(A1), self.L * np.sin(A2 + A3 + A4)])
        
        # Find the vectors for each arm segment by subtracting the positions of the joints
        AtB = B - A
        BtC = C - B
        CtD = D - C
        
        # Returns the vectors for each arm segment
        return AtB, BtC, CtD
    
    # Calls the solve_angles function by splitting a string and inputting it
    # Was used before I converted everything to vectors, but I kept it for fun
    def update_from_string(self, data_str):
        try:
            data = data_str.split(',')
            return self.solve_angles(float(data[0]), float(data[1]), float(data[2]))
        except (IndexError, ValueError):
            print("Invalid input format. Expected 'fx,fy,fz'.")
            return None

    # Calls the solve_vectors function by combining 3 values(x,y,z of a vector) and inputting it
    def update_from_vector(self, fx, fy, fz):
        return self.solve_vectors(float(fx), float(fy), float(fz))
    