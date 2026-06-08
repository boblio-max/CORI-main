"""
demo.py
Simple demo runner: starts the local ws_client server and loops a few safe poses
by writing to ws_client.data so connected clients (e.g. the Pi) will receive them.

Usage: python demo.py
"""

import threading
import time
import logging
import sys

# ensure package imports work
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '')))
from servers import ws_client

logging.basicConfig(level=logging.INFO, format='[demo] %(message)s')

# Safe poses (A1..A6). A1..A5 are 0..180, A6 is claw throttle -1..1
POSES = [
    [90, 90, 90, 90, 90, -1.0],   # neutral, claw open
    [80, 100, 95, 80, 100, 1.0],  # slightly forward, claw closed
    [110, 70, 110, 100, 80, -1.0],# raised pose, claw open
    [90, 60, 120, 70, 90, 0.0],   # mid pose, claw stop
]

INTERVAL = 3.0  # seconds per pose


def main():
    # start ws server so Pi or other clients can connect
    threading.Thread(target=ws_client.start_server, daemon=True).start()
    logging.info('ws_client server started (background thread)')

    try:
        while True:
            for pose in POSES:
                logging.info(f'Sending pose: {pose}')
                with ws_client.data_lock:
                    ws_client.data['A1'] = float(pose[0])
                    ws_client.data['A2'] = float(pose[1])
                    ws_client.data['A3'] = float(pose[2])
                    ws_client.data['A4'] = float(pose[3])
                    ws_client.data['A5'] = float(pose[4])
                    ws_client.data['A6'] = float(pose[5])
                time.sleep(INTERVAL)
    except KeyboardInterrupt:
        logging.info('Demo interrupted by user — exiting')


if __name__ == '__main__':
    main()
