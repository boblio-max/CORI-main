import subprocess
import os
import sys

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("Launching 3D Vector Visualizer...")
    vectors_process = subprocess.Popen(
        [sys.executable, os.path.join(script_dir, "3dvectors.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    print("Launching Main Dashboard...")
    dashboard_process = subprocess.Popen(
        [sys.executable, os.path.join(script_dir, "dashboard.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    print("All systems running. Close any window to exit.")
    vectors_process.wait()
    dashboard_process.wait()
    print("Shutting down.")