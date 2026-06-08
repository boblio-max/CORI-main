import subprocess
import os
import sys

# This script serves as the main orchestrator for launching both the 3D vector visualizer and the main dashboard.
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    
    # Launch the 3D vector visualizer in a separate process
    print("Launching 3D Vector Visualizer...")
    # Uses threads to run the visualizer in the background while the dashboard runs in the foreground
    vectors_process = subprocess.Popen(
        [sys.executable, os.path.join(parent_dir, "dashboard", "3d_vectors.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Launch the main dashboard in the main process
    print("Launching Main Dashboard...")
    dashboard_process = subprocess.Popen(
        [sys.executable, os.path.join(parent_dir, "dashboard", "dashboard.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for both processes to complete 
    print("All systems running. Close any window to exit.")
    vectors_process.wait()
    dashboard_process.wait()
    print("Shutting down.")
