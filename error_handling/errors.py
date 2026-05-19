# Error Handler - This keeps track of everything that could go wrong.
# It's like a dictionary of robot "bad moods" and how to describe them.
class Error:
    def __init__(self, type):
        self.type = type
        # These are the codes for different hardware failures.
        self.error_types = {1:"Robot Not working - Error not found", 
        11:"Rotate Base not working",
        12:"Shoulder Joint not working",
        13:"Elbow Joint not working",
        14:"Wrist Joint not working",
        15:"Rotate Grabber not working",
        16:"Grabber not working"}

        # Specific errors for when an angle is just too much to handle.
        self.angle_error = {1:"Angle out of bounds - Angle must be between 1 and 179 degrees"}

    # Placeholder for checking if an error is active.
    def isThrown(self:None) -> bool:
        return True
    
    # Grabs the actual error message based on the code.
    def get(self:None) -> int:
        try:
            return self.error_types[self.type]
        except KeyError:
            return self.error_types[1]
